# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-04-05

### Added
- Added lockscreen PIN navigation support for Xbox controller input using virtual keyboard-based lock input routing

### Fixed
- Fixed clean shutdown handling in `main`

### Documentation
- Clarified HDR limitations with nested gamescope on Hyprland

## [0.1.1] - 2026-04-03

### Changed
- Switched gamescope launching flow to Hyprland-managed execution
- Improved TV monitor activation through `hyprctl keyword monitor`

### Fixed
- Initial cleanup of gamescope session handling

## [0.1.0] - 2026-04-03

### Added
- Initial `nyxplay` implementation
- Xbox controller combo handling with evdev
- TV launch flow for gamescope through Hyprland
- Audio and microphone toggle actions
- Volume controls
- TOML-based configuration with dataclasses
- Rumble support
- Dedicated roadmap