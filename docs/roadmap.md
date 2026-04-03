# ROADMAP

## In Progress

### 1. Fix unreliable gamescope shutdown
**Problem:**
- `gamescope` does not always terminate properly
- `gamescopereaper` may remain running in the background
- orphaned processes can persist after session stop

**Tasks:**
- replace systemd-based stop with process-based shutdown
- terminate `gamescope` cleanly
- also terminate `gamescopereaper`
- add forced fallback (`SIGKILL`) if processes do not exit
- ensure no remaining processes after `LB + RB + B`

**Expected result:**
- reliable TV session shutdown
- no orphaned `gamescope` / `gamescopereaper` processes
- clean return to desktop state

---

### 2. Add HDR support
**Goal:**
- enable HDR support when launching gamescope on compatible displays

**Tasks:**
- identify correct HDR flags for gamescope
- integrate HDR options into `gamescope_command`
- make HDR configurable via `config.toml`
- test behavior on target TV
- verify compatibility with Steam Big Picture / Gamepad UI
- document SDR vs HDR behavior

**Expected result:**
- clean and optional HDR mode
- stable behavior on TV
- clear and maintainable configuration

---

## Next

### 3. Improve gamescope window placement robustness
**Tasks:**
- make workspace assignment more reliable
- improve window detection (gamescope client)
- eliminate focus-related side effects

---

### 4. Improve audio handling
**Tasks:**
- improve sink matching reliability (TV / desk)
- avoid ambiguous PipeWire names
- consider matching using more stable identifiers if needed

---

### 5. Refine project structure
**Tasks:**
- clarify separation between `actions.py`, `hyprland.py`, `launcher.py`
- reduce coupling between modules
- stabilize internal API design

---

## Later

### 6. User feedback improvements
**Ideas:**
- sound feedback for actions
- different rumble patterns (success / error / toggle)
- clearer notifications

---

### 7. Dev vs production configuration
**Ideas:**
- clean dev config fallback
- persistent user config override
- proper config layering (repo → user)

---

### 8. Packaging
**Ideas:**
- install default config properly
- finalize user systemd service
- prepare Arch package / AUR release