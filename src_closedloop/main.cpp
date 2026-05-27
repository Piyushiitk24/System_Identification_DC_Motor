// =============================================================================
// closed_loop_v1.cpp — Phase 3 closed-loop firmware (Stage 1 smoke build).
//
// Two operating modes:
//   1. CALIB — runs a 30-trial open-loop calibration (subset of Phase 2.1
//              conditions) so we can fit fresh Model A + Model C parameters
//              on bench day without swapping firmware. Trial table and runner
//              copied from src/main.cpp.
//   2. Closed-loop — runs one of four reference profiles (P1-P4) with one
//              of two controller personalities (BASE = global PI; CASC =
//              region-switched PI + inverse-static feedforward).
//
// Serial command set:
//   ?                                — print banner
//   WARMUP                           — run 2 long PWM=200 fwd/rev trials (~55 s motor-on)
//   CALIB                            — load CALIB mode (30-trial open-loop block)
//   DRIFT                            — run 6 end-of-session drift-check trials
//   BASE                             — load BASE controller (Model A)
//   CASC                             — load CASC controller (Model C)
//   LOAD P1 | P2 | P3 | P4           — select reference profile
//   GAINS_BASE <Kp> <Ki>             — set baseline PI gains (PWM/rpm, PWM/(rpm.s))
//   GAINS_CASC <accel_fwd_Kp> <accel_fwd_Ki> <decel_fwd_Kp> <decel_fwd_Ki>
//              <accel_rev_Kp> <accel_rev_Ki> <decel_rev_Kp> <decel_rev_Ki>
//   FF_FWD <n> <rpm0> <pwm0> <rpm1> <pwm1> ...  (n up to FF_MAX_POINTS)
//   FF_REV <n> <rpm0> <pwm0> ...
//   GO                               — execute current mode + selected profile
//   STOP                             — immediate active brake then disable
//
// Telemetry per sample inside trial blocks (10 ms intervals):
//   t_ms,profile,controller,ref_rpm,meas_rpm,pwm_cmd,dir,enc_count,integrator
// CALIB-mode trials reuse the open-loop schema:
//   t_ms,pwm_cmd,dir,enc_count,rpm
//
// Hardware: Arduino Uno R4 Minima + L298N + 12 V geared DC motor (same wiring
// as src/main.cpp; see PIN_CONFIGURATION.md).
//
// Safety:
//   - STOP triggers an active-brake sequence (IN1=IN2=HIGH at full duty for
//     150 ms) then coasts (ENA=0, IN1=IN2=LOW). Normal profile-end zero is
//     a coast, never a brake — matches identification convention.
//   - PWM output is clamped to [-255, 255] and slew-limited at 30 counts/sample.
//   - Loop-period self-check: a sample whose interval exceeds 25 ms triggers
//     an emergency stop (loop hang guard; full IWDT is a Stage-2 enhancement).
// =============================================================================

#include <Arduino.h>
#include "pwm.h"

// ----- Pin definitions -----
constexpr int PIN_ENC_A = 2;
constexpr int PIN_ENC_B = 3;
constexpr int PIN_IN1   = 4;
constexpr int PIN_IN2   = 5;
constexpr int PIN_ENA   = 9;

// ----- Encoder (identical to src/main.cpp) -----
constexpr int8_t ENCODER_SIGN   = -1;
constexpr float  COUNTS_PER_REV = 2400.0f;

volatile int32_t enc_count = 0;
volatile uint8_t enc_state = 0;

const int8_t ENC_LOOKUP[16] = {
     0, -1,  1,  0,
     1,  0,  0, -1,
    -1,  0,  0,  1,
     0,  1, -1,  0
};

void encISR() {
    uint8_t new_state = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);
    int8_t  delta     = ENC_LOOKUP[(enc_state << 2) | new_state];
    enc_count += ENCODER_SIGN * delta;
    enc_state  = new_state;
}

// ----- PWM and direction -----
PwmOut motorPwm(PIN_ENA);

inline void setPwmPercent(float pct) {
    if (pct < 0.0f)   pct = 0.0f;
    if (pct > 100.0f) pct = 100.0f;
    motorPwm.pulse_perc(pct);
}

void setPwmDuty(int pwm_0_255) {
    if (pwm_0_255 < 0)   pwm_0_255 = 0;
    if (pwm_0_255 > 255) pwm_0_255 = 255;
    setPwmPercent((float)pwm_0_255 * 100.0f / 255.0f);
}

void setDirection(int dir) {
    if (dir > 0) {
        digitalWrite(PIN_IN1, HIGH);
        digitalWrite(PIN_IN2, LOW);
    } else if (dir < 0) {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, HIGH);
    } else {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, LOW);
    }
}

void coastMotor() {
    // Normal zero-speed: disable ENA and de-assert direction lines.
    setPwmDuty(0);
    setDirection(0);
}

void emergencyBrake() {
    // Active brake: short the motor through the high-side transistors.
    setPwmPercent(100.0f);
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, HIGH);
    delay(150);
    setPwmPercent(0.0f);
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
}

// =============================================================================
// CALIB mode — open-loop 30-trial calibration block.
// Trial schema and runner are copies of src/main.cpp (which is the validated
// open-loop firmware). The 30 trials are: accel PWM in {160, 200, 240} x
// {fwd, rev} x 3 runs (18 trials) + decel 240->{0, 160} x {fwd, rev} x 3 runs
// (12 trials), matching the calibration plan.
// =============================================================================

struct Trial {
    const char* name;
    int      start_pwm;
    int      target_pwm;
    int      direction;     // +1 fwd, -1 rev
    uint32_t pre_step_ms;
    uint32_t post_step_ms;
};

// Combined trial table — split into three contiguous ranges:
//   [WARMUP_START, WARMUP_END)  -> WARMUP command
//   [CALIB_START,  CALIB_END)   -> CALIB  command  (the 30 calibration trials)
//   [DRIFT_START,  DRIFT_END)   -> DRIFT  command  (end-of-session drift check)
const Trial calib_trials[] = {
    // ----- Warm-up (2 trials, ~55 s motor-on) -----
    // 5 s settled at 0, then 20 s at PWM=200 fwd / rev. Names prefixed "warmup_"
    // so the fitting code can skip them.
    {"warmup_fwd_200",        0, 200, +1, 5000, 20000},
    {"warmup_rev_200",        0, 200, -1, 5000, 20000},

    // ----- Calibration block (30 trials) -----
    // accel PWM=160 x fwd x 3
    {"step_up_fwd_160_run01", 0, 160, +1,  500, 5000},
    {"step_up_fwd_160_run02", 0, 160, +1,  500, 5000},
    {"step_up_fwd_160_run03", 0, 160, +1,  500, 5000},
    // accel PWM=200 x fwd x 3
    {"step_up_fwd_200_run01", 0, 200, +1,  500, 5000},
    {"step_up_fwd_200_run02", 0, 200, +1,  500, 5000},
    {"step_up_fwd_200_run03", 0, 200, +1,  500, 5000},
    // accel PWM=240 x fwd x 3
    {"step_up_fwd_240_run01", 0, 240, +1,  500, 5000},
    {"step_up_fwd_240_run02", 0, 240, +1,  500, 5000},
    {"step_up_fwd_240_run03", 0, 240, +1,  500, 5000},
    // accel PWM=160 x rev x 3
    {"step_up_rev_160_run01", 0, 160, -1,  500, 5000},
    {"step_up_rev_160_run02", 0, 160, -1,  500, 5000},
    {"step_up_rev_160_run03", 0, 160, -1,  500, 5000},
    // accel PWM=200 x rev x 3
    {"step_up_rev_200_run01", 0, 200, -1,  500, 5000},
    {"step_up_rev_200_run02", 0, 200, -1,  500, 5000},
    {"step_up_rev_200_run03", 0, 200, -1,  500, 5000},
    // accel PWM=240 x rev x 3
    {"step_up_rev_240_run01", 0, 240, -1,  500, 5000},
    {"step_up_rev_240_run02", 0, 240, -1,  500, 5000},
    {"step_up_rev_240_run03", 0, 240, -1,  500, 5000},
    // decel 240->0 fwd x 3
    {"step_down_fwd_240to0_run01", 240, 0, +1, 3000, 5000},
    {"step_down_fwd_240to0_run02", 240, 0, +1, 3000, 5000},
    {"step_down_fwd_240to0_run03", 240, 0, +1, 3000, 5000},
    // decel 240->160 fwd x 3
    {"step_down_fwd_240to160_run01", 240, 160, +1, 3000, 5000},
    {"step_down_fwd_240to160_run02", 240, 160, +1, 3000, 5000},
    {"step_down_fwd_240to160_run03", 240, 160, +1, 3000, 5000},
    // decel 240->0 rev x 3
    {"step_down_rev_240to0_run01", 240, 0, -1, 3000, 5000},
    {"step_down_rev_240to0_run02", 240, 0, -1, 3000, 5000},
    {"step_down_rev_240to0_run03", 240, 0, -1, 3000, 5000},
    // decel 240->160 rev x 3
    {"step_down_rev_240to160_run01", 240, 160, -1, 3000, 5000},
    {"step_down_rev_240to160_run02", 240, 160, -1, 3000, 5000},
    {"step_down_rev_240to160_run03", 240, 160, -1, 3000, 5000},

    // ----- End-of-session drift check (6 trials) -----
    // Re-run PWM=200 accel in both directions x 3 to measure within-session
    // drift against the start-of-session calibration trials of the same name.
    {"drift_step_up_fwd_200_run01", 0, 200, +1,  500, 5000},
    {"drift_step_up_fwd_200_run02", 0, 200, +1,  500, 5000},
    {"drift_step_up_fwd_200_run03", 0, 200, +1,  500, 5000},
    {"drift_step_up_rev_200_run01", 0, 200, -1,  500, 5000},
    {"drift_step_up_rev_200_run02", 0, 200, -1,  500, 5000},
    {"drift_step_up_rev_200_run03", 0, 200, -1,  500, 5000},
};
const int NUM_CALIB_TRIALS = sizeof(calib_trials) / sizeof(calib_trials[0]);

constexpr int WARMUP_START = 0;
constexpr int WARMUP_END   = 2;
constexpr int CALIB_START  = 2;
constexpr int CALIB_END    = 32;
constexpr int DRIFT_START  = 32;
constexpr int DRIFT_END    = 38;

constexpr uint32_t LOG_INTERVAL_US     = 10000;
constexpr uint32_t INTER_TRIAL_REST_MS = 3000;

void runCalibTrial(const Trial& t) {
    coastMotor();
    delay(INTER_TRIAL_REST_MS);

    Serial.print(F("=== START "));
    Serial.print(t.name);
    Serial.println(F(" ==="));
    Serial.println(F("t_ms,pwm_cmd,dir,enc_count,rpm"));

    noInterrupts();
    enc_count = 0;
    interrupts();
    int32_t prev_count = 0;

    int current_pwm = t.start_pwm;
    int current_dir = t.direction;
    setDirection(current_pwm > 0 ? current_dir : 0);
    setPwmDuty(current_pwm);

    uint32_t trial_start_us = micros();
    uint32_t prev_us        = trial_start_us;
    uint32_t step_time_us   = trial_start_us + t.pre_step_ms * 1000UL;
    uint32_t end_time_us    = step_time_us   + t.post_step_ms * 1000UL;
    uint32_t next_log_us    = trial_start_us;

    bool stepped = false;

    while ((int32_t)(micros() - end_time_us) < 0) {
        uint32_t now_us = micros();

        if (!stepped && (int32_t)(now_us - step_time_us) >= 0) {
            current_pwm = t.target_pwm;
            setDirection(current_pwm > 0 ? current_dir : 0);
            setPwmDuty(current_pwm);
            stepped = true;
        }

        if ((int32_t)(now_us - next_log_us) >= 0) {
            int32_t cnt;
            noInterrupts();
            cnt = enc_count;
            interrupts();

            int32_t  delta_cnt = cnt - prev_count;
            uint32_t delta_us  = now_us - prev_us;
            float    rpm       = 0.0f;
            if (delta_us > 0) {
                rpm = ((float)delta_cnt * 60.0e6f) / (COUNTS_PER_REV * (float)delta_us);
            }

            uint32_t t_ms = (now_us - trial_start_us) / 1000;
            char dir_char = (current_pwm == 0) ? 'N' : (current_dir > 0 ? 'F' : 'R');

            Serial.print(t_ms);
            Serial.print(',');
            Serial.print(current_pwm);
            Serial.print(',');
            Serial.print(dir_char);
            Serial.print(',');
            Serial.print(cnt);
            Serial.print(',');
            Serial.println(rpm, 2);

            prev_count   = cnt;
            prev_us      = now_us;
            next_log_us += LOG_INTERVAL_US;
        }
    }

    coastMotor();
    Serial.println(F("=== END ==="));
    Serial.flush();
}

// =============================================================================
// Controllers (BASE / CASC) and FF table.
//
// The Python sim implementation in motor_id/controllers.py is the reference;
// this is its C++ counterpart and must match it sample-for-sample modulo
// floating-point order.
// =============================================================================

constexpr float DT_S          = 0.010f;
constexpr float PWM_MAX       = 255.0f;
constexpr float PWM_SLEW      = 30.0f;        // max |delta PWM| per sample
constexpr int   FF_MAX_POINTS = 8;

struct PIGains { float Kp = 0.0f; float Ki = 0.0f; };

// BASE controller state
PIGains g_base;
// CASC controller: four sets (accel_fwd, decel_fwd, accel_rev, decel_rev)
PIGains g_acc_fwd, g_dec_fwd, g_acc_rev, g_dec_rev;

// FF table (per direction)
int   ff_fwd_n = 0;
float ff_fwd_rpm[FF_MAX_POINTS];
float ff_fwd_pwm[FF_MAX_POINTS];
int   ff_rev_n = 0;
float ff_rev_rpm[FF_MAX_POINTS];
float ff_rev_pwm[FF_MAX_POINTS];

// Controller integrator and previous output (reset before each trial)
float ctrl_integrator   = 0.0f;
float ctrl_prev_output  = 0.0f;

void resetController() {
    ctrl_integrator  = 0.0f;
    ctrl_prev_output = 0.0f;
}

// Piecewise-linear lookup; saturates at endpoints. Returns 0 for rpm_target=0.
float ffLookup(float rpm_target) {
    if (rpm_target == 0.0f) return 0.0f;
    bool fwd = rpm_target > 0.0f;
    float mag = fwd ? rpm_target : -rpm_target;
    int   n   = fwd ? ff_fwd_n : ff_rev_n;
    if (n == 0) return 0.0f;
    const float* rpms = fwd ? ff_fwd_rpm : ff_rev_rpm;
    const float* pwms = fwd ? ff_fwd_pwm : ff_rev_pwm;
    float pwm;
    if (mag <= rpms[0]) {
        pwm = pwms[0];
    } else if (mag >= rpms[n - 1]) {
        pwm = pwms[n - 1];
    } else {
        int i = 0;
        while (i + 1 < n && rpms[i + 1] < mag) ++i;
        float t = (mag - rpms[i]) / (rpms[i + 1] - rpms[i]);
        pwm = pwms[i] + t * (pwms[i + 1] - pwms[i]);
    }
    return fwd ? pwm : -pwm;
}

// One control-loop step. Returns signed PWM command (clamped, slew-limited).
//   ctrl_mode: 0 = BASE, 1 = CASC
float controlStep(int ctrl_mode, float ref, float meas) {
    PIGains g;
    float u_ff = 0.0f;
    if (ctrl_mode == 0) {
        g = g_base;
    } else {
        // region: accel when speed magnitude is growing (same sign of ref and ref-meas)
        bool accel;
        if (ref == 0.0f) {
            accel = false;
        } else {
            float sign_ref = (ref > 0.0f) ? 1.0f : -1.0f;
            accel = (sign_ref * (ref - meas) > 0.0f) && (sign_ref * meas >= 0.0f);
        }
        if (ref >= 0.0f) g = accel ? g_acc_fwd : g_dec_fwd;
        else             g = accel ? g_acc_rev : g_dec_rev;
        u_ff = ffLookup(ref);
    }
    float error = ref - meas;
    float new_int = ctrl_integrator + error * DT_S;
    float u_pi    = g.Kp * error + g.Ki * new_int;
    float u_unsat = u_ff + u_pi;
    float u_sat   = u_unsat;
    if (u_sat >  PWM_MAX) u_sat =  PWM_MAX;
    if (u_sat < -PWM_MAX) u_sat = -PWM_MAX;
    bool saturated = (u_unsat != u_sat);
    // anti-windup: do not integrate further into saturation
    if (!(saturated && (error * (u_unsat - u_ff) > 0.0f))) {
        ctrl_integrator = new_int;
    }
    // output slew limit
    float u_out = u_sat;
    if (u_out > ctrl_prev_output + PWM_SLEW) u_out = ctrl_prev_output + PWM_SLEW;
    if (u_out < ctrl_prev_output - PWM_SLEW) u_out = ctrl_prev_output - PWM_SLEW;
    ctrl_prev_output = u_out;
    return u_out;
}

// =============================================================================
// Reference profiles (P1-P4) — piecewise breakpoints.
//
// Each profile is an array of {t_ms, ref_rpm} breakpoints. At runtime,
// refLookup(profile, t) does linear interpolation between adjacent breakpoints
// (so ramps and holds are both expressible). Profiles must be monotone-in-time.
// =============================================================================

struct RefPoint { uint32_t t_ms; float ref_rpm; };

// P1 — bidirectional staircase, 3 s holds.
// 0 -> +80 -> +150 -> +200 -> +150 -> +80 -> 0 -> -80 -> -150 -> -200 ->
// -150 -> -80 -> 0  (13 levels, 12 transitions, 39 s total).
// Encoded as: 13 hold-end breakpoints; transitions are zero-width steps.
const RefPoint P1_pts[] = {
    {0,        0},   {3000,     0},
    {3000,    80},   {6000,    80},
    {6000,   150},   {9000,   150},
    {9000,   200},  {12000,   200},
    {12000,  150},  {15000,   150},
    {15000,   80},  {18000,    80},
    {18000,    0},  {21000,     0},
    {21000,  -80},  {24000,   -80},
    {24000, -150},  {27000,  -150},
    {27000, -200},  {30000,  -200},
    {30000, -150},  {33000,  -150},
    {33000,  -80},  {36000,   -80},
    {36000,    0},  {39000,     0},
};
const int P1_N = sizeof(P1_pts) / sizeof(P1_pts[0]);

// P2 — bidirectional ramp through deadzone.
// 0 -> +150 (10 s ramp), hold +150 (5 s), +150 -> 0 (10 s ramp), hold 0 (3 s),
// 0 -> -150 (10 s ramp), hold -150 (5 s), -150 -> 0 (10 s ramp). Total 53 s.
const RefPoint P2_pts[] = {
    {0,          0},
    {10000,    150},
    {15000,    150},
    {25000,      0},
    {28000,      0},
    {38000,   -150},
    {43000,   -150},
    {53000,      0},
};
const int P2_N = sizeof(P2_pts) / sizeof(P2_pts[0]);

// P3 — reversal: +100 hold 3 s -> ramp to -100 over 4 s -> hold -100 3 s.
const RefPoint P3_pts[] = {
    {0,      100},
    {3000,   100},
    {7000,  -100},
    {10000, -100},
};
const int P3_N = sizeof(P3_pts) / sizeof(P3_pts[0]);

// P4 — small-signal negative control: 150 -> 160 -> 150 -> 160, 2 s holds.
const RefPoint P4_pts[] = {
    {0,      150},  {2000,   150},
    {2000,   160},  {4000,   160},
    {4000,   150},  {6000,   150},
    {6000,   160},  {8000,   160},
};
const int P4_N = sizeof(P4_pts) / sizeof(P4_pts[0]);

struct ProfileDef {
    const char*     name;
    const RefPoint* pts;
    int             n;
};
const ProfileDef PROFILES[] = {
    {"P1", P1_pts, P1_N},
    {"P2", P2_pts, P2_N},
    {"P3", P3_pts, P3_N},
    {"P4", P4_pts, P4_N},
};
const int NUM_PROFILES = sizeof(PROFILES) / sizeof(PROFILES[0]);

float refLookup(const ProfileDef& p, uint32_t t_ms) {
    if (p.n == 0) return 0.0f;
    if (t_ms <= p.pts[0].t_ms) return p.pts[0].ref_rpm;
    if (t_ms >= p.pts[p.n - 1].t_ms) return p.pts[p.n - 1].ref_rpm;
    int i = 0;
    while (i + 1 < p.n && p.pts[i + 1].t_ms < t_ms) ++i;
    uint32_t t0 = p.pts[i].t_ms, t1 = p.pts[i + 1].t_ms;
    if (t1 == t0) return p.pts[i + 1].ref_rpm;
    float u = (float)(t_ms - t0) / (float)(t1 - t0);
    return p.pts[i].ref_rpm + u * (p.pts[i + 1].ref_rpm - p.pts[i].ref_rpm);
}

uint32_t profileDurationMs(const ProfileDef& p) {
    return p.n > 0 ? p.pts[p.n - 1].t_ms : 0;
}

// =============================================================================
// Closed-loop trial runner.
// =============================================================================

constexpr uint32_t LOOP_HANG_THRESHOLD_US = 25000;  // 2.5 x nominal 10 ms

void runClosedLoopTrial(int ctrl_mode, int profile_idx) {
    if (profile_idx < 0 || profile_idx >= NUM_PROFILES) return;
    const ProfileDef& prof = PROFILES[profile_idx];
    const char* ctrl_name = (ctrl_mode == 0) ? "BASE" : "CASC";

    coastMotor();
    delay(INTER_TRIAL_REST_MS);

    Serial.print(F("=== START "));
    Serial.print(prof.name);
    Serial.print(F("_"));
    Serial.print(ctrl_name);
    Serial.println(F(" ==="));
    Serial.println(F("t_ms,profile,controller,ref_rpm,meas_rpm,pwm_cmd,dir,enc_count,integrator"));

    noInterrupts();
    enc_count = 0;
    interrupts();
    int32_t prev_count = 0;
    resetController();

    uint32_t trial_start_us = micros();
    uint32_t prev_us        = trial_start_us;
    uint32_t next_log_us    = trial_start_us;
    uint32_t duration_us    = profileDurationMs(prof) * 1000UL;
    uint32_t end_time_us    = trial_start_us + duration_us;

    bool emergency = false;
    while ((int32_t)(micros() - end_time_us) < 0) {
        uint32_t now_us = micros();

        // Loop-hang self-check: if the inter-sample gap blows past
        // LOOP_HANG_THRESHOLD_US, abort.
        if ((int32_t)(now_us - next_log_us) > (int32_t)LOOP_HANG_THRESHOLD_US) {
            emergency = true;
            break;
        }

        if ((int32_t)(now_us - next_log_us) >= 0) {
            int32_t cnt;
            noInterrupts();
            cnt = enc_count;
            interrupts();

            int32_t  delta_cnt = cnt - prev_count;
            uint32_t delta_us  = now_us - prev_us;
            float    meas_rpm  = 0.0f;
            if (delta_us > 0) {
                meas_rpm = ((float)delta_cnt * 60.0e6f) / (COUNTS_PER_REV * (float)delta_us);
            }

            uint32_t t_ms = (now_us - trial_start_us) / 1000;
            float ref     = refLookup(prof, t_ms);
            float u_cmd   = controlStep(ctrl_mode, ref, meas_rpm);

            int   pwm_mag = (int)(u_cmd >= 0 ? u_cmd : -u_cmd);
            int   dir_int = (u_cmd > 0) - (u_cmd < 0);
            setDirection(dir_int);
            setPwmDuty(pwm_mag);
            char dir_char = (pwm_mag == 0) ? 'N' : (dir_int > 0 ? 'F' : 'R');

            Serial.print(t_ms);
            Serial.print(',');
            Serial.print(prof.name);
            Serial.print(',');
            Serial.print(ctrl_name);
            Serial.print(',');
            Serial.print(ref, 2);
            Serial.print(',');
            Serial.print(meas_rpm, 2);
            Serial.print(',');
            Serial.print((int)u_cmd);
            Serial.print(',');
            Serial.print(dir_char);
            Serial.print(',');
            Serial.print(cnt);
            Serial.print(',');
            Serial.println(ctrl_integrator, 4);

            prev_count   = cnt;
            prev_us      = now_us;
            next_log_us += LOG_INTERVAL_US;
        }
    }

    coastMotor();
    if (emergency) {
        Serial.println(F("# EMERGENCY: loop-hang threshold exceeded, motor coasted"));
    }
    Serial.println(F("=== END ==="));
    Serial.flush();
}

// =============================================================================
// State machine and command parser.
// =============================================================================

enum Mode { MODE_NONE, MODE_CALIB, MODE_WARMUP, MODE_DRIFT, MODE_CLOSED };
Mode g_mode = MODE_NONE;
int  g_controller = -1;    // 0 = BASE, 1 = CASC
int  g_profile    = -1;    // index into PROFILES

constexpr uint32_t READY_PRINT_MS = 5000;

void printBanner() {
    Serial.println(F("# closed_loop_v1 ready (Phase 3 Stage 1 smoke)"));
    Serial.println(F("# Commands: ? CALIB BASE CASC LOAD P1|P2|P3|P4"));
    Serial.println(F("#           GAINS_BASE <Kp> <Ki>"));
    Serial.println(F("#           GAINS_CASC <Kp_af> <Ki_af> <Kp_df> <Ki_df>"
                     " <Kp_ar> <Ki_ar> <Kp_dr> <Ki_dr>"));
    Serial.println(F("#           FF_FWD <n> <rpm0> <pwm0> ..."));
    Serial.println(F("#           FF_REV <n> <rpm0> <pwm0> ..."));
    Serial.println(F("#           GO STOP"));
    Serial.print  (F("# mode="));
    Serial.print(g_mode == MODE_CALIB  ? "CALIB"  :
                 g_mode == MODE_WARMUP ? "WARMUP" :
                 g_mode == MODE_DRIFT  ? "DRIFT"  :
                 g_mode == MODE_CLOSED ? "CLOSED" : "NONE");
    Serial.print  (F("  controller="));
    Serial.print(g_controller == 0 ? "BASE" : (g_controller == 1 ? "CASC" : "?"));
    Serial.print  (F("  profile="));
    if (g_profile >= 0 && g_profile < NUM_PROFILES) Serial.println(PROFILES[g_profile].name);
    else Serial.println("?");
}

// Parse up to `expected` whitespace-separated floats from `s` (modifies s).
// Returns number actually parsed.
int parseFloats(char* s, float* out, int expected) {
    int n = 0;
    char* tok = strtok(s, " \t\r\n");
    while (tok != nullptr && n < expected) {
        out[n++] = atof(tok);
        tok = strtok(nullptr, " \t\r\n");
    }
    return n;
}

bool handleGainsBase(char* args) {
    float v[2];
    if (parseFloats(args, v, 2) != 2) return false;
    g_base.Kp = v[0]; g_base.Ki = v[1];
    Serial.print(F("# BASE gains: Kp="));
    Serial.print(g_base.Kp, 4);
    Serial.print(F(" Ki="));
    Serial.println(g_base.Ki, 4);
    return true;
}

bool handleGainsCasc(char* args) {
    float v[8];
    if (parseFloats(args, v, 8) != 8) return false;
    g_acc_fwd = {v[0], v[1]};
    g_dec_fwd = {v[2], v[3]};
    g_acc_rev = {v[4], v[5]};
    g_dec_rev = {v[6], v[7]};
    Serial.println(F("# CASC gains loaded:"));
    Serial.print(F("#   accel_fwd Kp=")); Serial.print(g_acc_fwd.Kp, 4);
    Serial.print(F(" Ki="));               Serial.println(g_acc_fwd.Ki, 4);
    Serial.print(F("#   decel_fwd Kp=")); Serial.print(g_dec_fwd.Kp, 4);
    Serial.print(F(" Ki="));               Serial.println(g_dec_fwd.Ki, 4);
    Serial.print(F("#   accel_rev Kp=")); Serial.print(g_acc_rev.Kp, 4);
    Serial.print(F(" Ki="));               Serial.println(g_acc_rev.Ki, 4);
    Serial.print(F("#   decel_rev Kp=")); Serial.print(g_dec_rev.Kp, 4);
    Serial.print(F(" Ki="));               Serial.println(g_dec_rev.Ki, 4);
    return true;
}

bool handleFF(char* args, bool fwd) {
    char* tok = strtok(args, " \t\r\n");
    if (!tok) return false;
    int n = atoi(tok);
    if (n < 1 || n > FF_MAX_POINTS) return false;
    float* rpms = fwd ? ff_fwd_rpm : ff_rev_rpm;
    float* pwms = fwd ? ff_fwd_pwm : ff_rev_pwm;
    for (int i = 0; i < n; ++i) {
        char* tr = strtok(nullptr, " \t\r\n");
        char* tp = strtok(nullptr, " \t\r\n");
        if (!tr || !tp) return false;
        rpms[i] = atof(tr);
        pwms[i] = atof(tp);
    }
    if (fwd) ff_fwd_n = n; else ff_rev_n = n;
    Serial.print(F("# FF_"));
    Serial.print(fwd ? "FWD" : "REV");
    Serial.print(F(" loaded ("));
    Serial.print(n);
    Serial.println(F(" pts)"));
    return true;
}

bool handleLoad(char* args) {
    char* tok = strtok(args, " \t\r\n");
    if (!tok) return false;
    for (int i = 0; i < NUM_PROFILES; ++i) {
        if (strcmp(tok, PROFILES[i].name) == 0) {
            g_profile = i;
            g_mode = MODE_CLOSED;
            Serial.print(F("# Profile selected: "));
            Serial.print(PROFILES[i].name);
            Serial.print(F("  duration="));
            Serial.print(profileDurationMs(PROFILES[i]));
            Serial.println(F(" ms"));
            return true;
        }
    }
    return false;
}

void runCalibRange(int start, int end, const char* label) {
    Serial.print(F("# === "));
    Serial.print(label);
    Serial.println(F(" SEQUENCE START ==="));
    for (int i = start; i < end; ++i) {
        Serial.print(F("# "));
        Serial.print(label);
        Serial.print(F(" trial "));
        Serial.print(i - start + 1);
        Serial.print(F(" of "));
        Serial.print(end - start);
        Serial.print(F(": "));
        Serial.println(calib_trials[i].name);
        runCalibTrial(calib_trials[i]);
    }
    coastMotor();
    Serial.print(F("# === "));
    Serial.print(label);
    Serial.println(F(" SEQUENCE COMPLETE ==="));
}

void doGo() {
    if (g_mode == MODE_CALIB) {
        runCalibRange(CALIB_START, CALIB_END, "CALIB");
    } else if (g_mode == MODE_WARMUP) {
        runCalibRange(WARMUP_START, WARMUP_END, "WARMUP");
    } else if (g_mode == MODE_DRIFT) {
        runCalibRange(DRIFT_START, DRIFT_END, "DRIFT");
    } else if (g_mode == MODE_CLOSED) {
        if (g_controller < 0) { Serial.println(F("# ERROR: no controller selected")); return; }
        if (g_profile    < 0) { Serial.println(F("# ERROR: no profile loaded")); return; }
        Serial.println(F("# === CLOSED-LOOP TRIAL START ==="));
        runClosedLoopTrial(g_controller, g_profile);
        coastMotor();
        Serial.println(F("# === CLOSED-LOOP TRIAL COMPLETE ==="));
    } else {
        Serial.println(F("# ERROR: no mode set (CALIB or LOAD Pn)"));
    }
}

void parseCommand(String line) {
    line.trim();
    if (line.length() == 0) return;

    if (line == "?") { printBanner(); return; }
    if (line == "STOP") { emergencyBrake(); Serial.println(F("# Motor stopped (active brake)")); return; }
    if (line == "GO")   { doGo(); return; }

    if (line == "CALIB") {
        g_mode = MODE_CALIB;
        Serial.println(F("# Mode: CALIB (open-loop 30-trial)"));
        return;
    }
    if (line == "WARMUP") {
        g_mode = MODE_WARMUP;
        Serial.println(F("# Mode: WARMUP (2 long trials)"));
        return;
    }
    if (line == "DRIFT") {
        g_mode = MODE_DRIFT;
        Serial.println(F("# Mode: DRIFT (6 end-of-session trials)"));
        return;
    }
    if (line == "BASE") {
        g_controller = 0;
        if (g_mode == MODE_NONE) g_mode = MODE_CLOSED;
        Serial.println(F("# Controller: BASE"));
        return;
    }
    if (line == "CASC") {
        g_controller = 1;
        if (g_mode == MODE_NONE) g_mode = MODE_CLOSED;
        Serial.println(F("# Controller: CASC"));
        return;
    }

    // Commands with arguments
    int sp = line.indexOf(' ');
    String head = sp > 0 ? line.substring(0, sp) : line;
    String tail = sp > 0 ? line.substring(sp + 1) : String("");
    char buf[256]; tail.toCharArray(buf, sizeof(buf));

    bool ok = false;
    if      (head == "LOAD")        ok = handleLoad(buf);
    else if (head == "GAINS_BASE")  ok = handleGainsBase(buf);
    else if (head == "GAINS_CASC")  ok = handleGainsCasc(buf);
    else if (head == "FF_FWD")      ok = handleFF(buf, true);
    else if (head == "FF_REV")      ok = handleFF(buf, false);
    else {
        Serial.print(F("# Unknown command: "));
        Serial.println(line);
        return;
    }
    if (!ok) {
        Serial.print(F("# Bad arguments to "));
        Serial.println(head);
    }
}

// =============================================================================
// Setup / loop
// =============================================================================

void setup() {
    pinMode(PIN_ENC_A, INPUT_PULLUP);
    pinMode(PIN_ENC_B, INPUT_PULLUP);
    pinMode(PIN_IN1,   OUTPUT);
    pinMode(PIN_IN2,   OUTPUT);

    enc_state = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);

    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), encISR, CHANGE);

    Serial.begin(230400);
    while (!Serial && millis() < 3000) {}

    motorPwm.begin(20000.0f, 0.0f);
    motorPwm.pulse_perc(0.0f);
    coastMotor();
    delay(2000);

    printBanner();
}

void loop() {
    static uint32_t last_ready_print_ms = 0;
    if (millis() - last_ready_print_ms >= READY_PRINT_MS) {
        printBanner();
        last_ready_print_ms = millis();
    }

    if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        parseCommand(cmd);
    }
}
