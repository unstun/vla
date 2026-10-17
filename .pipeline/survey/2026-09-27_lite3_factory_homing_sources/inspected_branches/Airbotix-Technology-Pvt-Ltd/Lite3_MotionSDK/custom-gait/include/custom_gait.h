/**
 * @file custom_gait.h
 * @brief Example custom trot and crawl gaits for the Jueying Lite3.
 */

#pragma once

#include "sim_robot_types.h"
#include <cmath>
#include <array>
#include <string>
#include <algorithm>

// ─── Robot geometry (Lite3) ──────────────────────────────────────────────────
static constexpr float THIGH_LEN   = 0.213f; // m
static constexpr float SHANK_LEN   = 0.213f; // m
static constexpr float STAND_HEIGHT = 0.3f;   // m
static constexpr float STEP_HEIGHT  = 0.08f; // m

// ─── Trot parameters ─────────────────────────────────────────────────────────
static constexpr float TROT_PERIOD      = 0.35f;
static constexpr float STANCE_FRACTION  = 0.6f;

// ─── Default joint clamping ───────────────────────────────────────────────────
static constexpr float HIP_X_DEFAULT = 0.f;
static constexpr float HIP_Y_DEFAULT = -0.785f;  // ≈ -45 deg
static constexpr float KNEE_DEFAULT  =  1.571f;  // ≈ +90 deg

// ─── Gains ────────────────────────────────────────────────────────────────────
static constexpr float STANCE_KP = 120.f;
static constexpr float STANCE_KD =   3.5f;
static constexpr float SWING_KP  =  60.f;
static constexpr float SWING_KD  =   2.0f;

class CustomGait {
public:
    CustomGait() = default;

    // ── PUBLIC: Stand ────────────────────────────────────────────────────────
    bool StandUp(SimRobotCmd& cmd, double elapsed, const SimRobotData& data,
                 double duration = 2.0)
    {
        if (!stand_init_) {
            for (int i = 0; i < 12; ++i)
                stand_init_pos_[i] = data.joint_data.joint_data[i].position;
            stand_init_ = true;
        }

        float alpha = static_cast<float>(std::min(elapsed / duration, 1.0));
        alpha = SmoothStep(alpha);

        const float target[3] = { HIP_X_DEFAULT, HIP_Y_DEFAULT, KNEE_DEFAULT };

        for (int leg = 0; leg < 4; ++leg) {
            for (int j = 0; j < 3; ++j) {
                int idx = leg * 3 + j;
                cmd.joint_cmd[idx].position = Lerp(stand_init_pos_[idx], target[j], alpha);
                cmd.joint_cmd[idx].velocity = 0.f;
                cmd.joint_cmd[idx].torque   = 0.f;
                cmd.joint_cmd[idx].kp       = STANCE_KP;
                cmd.joint_cmd[idx].kd       = STANCE_KD;
            }
        }
        return (elapsed >= duration);
    }

    // ── PUBLIC: Trot ─────────────────────────────────────────────────────────
    void Trot(SimRobotCmd& cmd, double elapsed,
              float vx = 0.f, float vy = 0.f, float wz = 0.f)
    {
        const float T = trot_period_;
        double t = std::fmod(elapsed, T);
        float phaseA = static_cast<float>(t / T);
        float phaseB = std::fmod(phaseA + 0.5f, 1.f);

        float leg_phase[4] = { phaseA, phaseB, phaseB, phaseA };
        const float lr[4]  = { -1.f, +1.f, -1.f, +1.f };
        const float YAW_R  = 0.15f;

        for (int leg = 0; leg < 4; ++leg) {
            float vx_eff = vx + wz * lr[leg] * YAW_R;
            SetLegFromPhase(cmd, leg, leg_phase[leg], vx_eff, vy);
        }
    }

    // ── PUBLIC: Crawl (stair gait) ───────────────────────────────────────────
    void Crawl(SimRobotCmd& cmd, double elapsed,
               float vx = 0.f, float vy = 0.f, float wz = 0.f)
    {
        const float T          = trot_period_;
        const float SWING_FRAC = 0.25f;

        float phase = static_cast<float>(std::fmod(elapsed / T, 1.0));
        const float offset[4] = { 0.25f, 0.75f, 0.00f, 0.50f };
        float body_x = (phase < 0.5f) ? +0.07f : -0.07f;

        for (int leg = 0; leg < 4; ++leg) {
            float local = std::fmod(phase - offset[leg] + 1.f, 1.f);
            bool  is_swing = (local < SWING_FRAC);
            float kp = is_swing ? SWING_KP : STANCE_KP;
            float kd = is_swing ? SWING_KD : STANCE_KD;
            int   base = leg * 3;

            auto sweep = [&](float amp) -> float {
                if (is_swing) {
                    float s = local / SWING_FRAC;
                    return amp * (2.f * s - 1.f);
                } else {
                    float s = (local - SWING_FRAC) / (1.f - SWING_FRAC);
                    return amp * (1.f - 2.f * s);
                }
            };

            float hip_y_bias = sweep(-vx * stride_scale_);

            float pitch_sign = (leg <= 1) ? +1.f : -1.f;
            float total_pitch = body_pitch_ + manual_pitch_off_;
            float hip_y = HIP_Y_DEFAULT + hip_y_bias + pitch_sign * total_pitch;
            hip_y = std::clamp(hip_y, -1.5f, 0.0f);

            float hip_x = HIP_X_DEFAULT + body_x + vy * 0.25f;
            hip_x = std::clamp(hip_x, -0.4f, 0.4f);

            float knee = KNEE_DEFAULT;
            if (is_swing) {
                float s = local / SWING_FRAC;
                knee += knee_lift_ * std::sin(static_cast<float>(M_PI) * s);
            }
            knee = std::clamp(knee, 0.5f, 2.5f);

            for (int j = 0; j < 3; ++j) {
                cmd.joint_cmd[base + j].position = (j == 0 ? hip_x : (j == 1 ? hip_y : knee));
                cmd.joint_cmd[base + j].velocity = 0.f;
                cmd.joint_cmd[base + j].torque   = 0.f;
                cmd.joint_cmd[base + j].kp       = kp;
                cmd.joint_cmd[base + j].kd       = kd;
            }
        }
    }

    void Hold(SimRobotCmd& cmd) {
        for (int i = 0; i < 12; ++i) {
            int j = i % 3;
            cmd.joint_cmd[i].position = (j == 0 ? HIP_X_DEFAULT : (j == 1 ? HIP_Y_DEFAULT : KNEE_DEFAULT));
            cmd.joint_cmd[i].velocity = 0.f;
            cmd.joint_cmd[i].torque   = 0.f;
            cmd.joint_cmd[i].kp       = STANCE_KP;
            cmd.joint_cmd[i].kd       = STANCE_KD;
        }
    }

    void JointDamping(SimRobotCmd& cmd) {
        for (int i = 0; i < 12; ++i) {
            cmd.joint_cmd[i].position = 0.f;
            cmd.joint_cmd[i].velocity = 0.f;
            cmd.joint_cmd[i].torque   = 0.f;
            cmd.joint_cmd[i].kp       = 0.f;
            cmd.joint_cmd[i].kd       = 2.f;
        }
    }

    void ResetStand() { stand_init_ = false; }

    void SetStairMode(bool stair) {
        if (stair) {
            trot_period_  = 0.70f;
            knee_lift_    = 1.20f;
            stride_scale_ = 0.55f;
            body_pitch_   = 0.15f;
        } else {
            trot_period_  = TROT_PERIOD;
            knee_lift_    = 0.65f;
            stride_scale_ = 0.40f;
            body_pitch_   = 0.0f;
        }
    }

    /** Manual tweak for slopes: adds to the base gait pitch */
    void SetPitchOffset(float off) { manual_pitch_off_ = off; }

private:
    bool  stand_init_ = false;
    float stand_init_pos_[12]{};

    float trot_period_  = TROT_PERIOD;
    float knee_lift_    = 0.65f;
    float stride_scale_ = 0.40f;
    float body_pitch_   = 0.0f;
    float manual_pitch_off_ = 0.f;  // added via setter

    float SmoothStep(float t) const {
        t = std::clamp(t, 0.f, 1.f);
        return t * t * (3.f - 2.f * t);
    }

    float Lerp(float a, float b, float t) const { return a + t * (b - a); }

    void SetLegFromPhase(SimRobotCmd& cmd, int leg, float phase,
                         float vx_eff, float vy)
    {
        bool  is_stance = (phase < STANCE_FRACTION);
        float kp = is_stance ? STANCE_KP : SWING_KP;
        float kd = is_stance ? STANCE_KD : SWING_KD;
        int   base = leg * 3;

        auto sweep = [&](float amp) -> float {
            if (is_stance) {
                float s = phase / STANCE_FRACTION;
                return amp * (2.f * s - 1.f);
            } else {
                float s = (phase - STANCE_FRACTION) / (1.f - STANCE_FRACTION);
                return amp * (1.f - 2.f * s);
            }
        };

        float pitch_sign = (leg <= 1) ? +1.f : -1.f;
        float total_pitch = body_pitch_ + manual_pitch_off_;
        float hip_y = HIP_Y_DEFAULT + sweep(-vx_eff * stride_scale_) + pitch_sign * total_pitch;
        hip_y = std::clamp(hip_y, -1.5f, 0.0f);

        float hip_x = HIP_X_DEFAULT + sweep(vy * 0.25f);
        hip_x = std::clamp(hip_x, -0.4f, 0.4f);

        float knee = KNEE_DEFAULT;
        if (!is_stance) {
            float s = (phase - STANCE_FRACTION) / (1.f - STANCE_FRACTION);
            knee += knee_lift_ * std::sin(static_cast<float>(M_PI) * s);
        }
        knee = std::clamp(knee, 0.5f, 2.5f);

        for (int j = 0; j < 3; ++j) {
            cmd.joint_cmd[base + j].position = (j == 0 ? hip_x : (j == 1 ? hip_y : knee));
            cmd.joint_cmd[base + j].velocity = 0.f;
            cmd.joint_cmd[base + j].torque   = 0.f;
            cmd.joint_cmd[base + j].kp       = kp;
            cmd.joint_cmd[base + j].kd       = kd;
        }
    }
};
