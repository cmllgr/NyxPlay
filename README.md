# NyxPlay

Daemon Python pour écouter une manette Xbox et déclencher des actions système sous Linux.

## Features

- LB + RB combo actions
- Volume control with D-pad
- Hold LT + RT for poweroff
- User configuration in TOML
- Custom action scripts
- systemd user service

## Requirements

Core runtime:
- python
- python-evdev

Optional tools used by the default example scripts:
- libnotify (`notify-send`)
- wireplumber (`wpctl`)
- hyprland (`hyprctl`)
- steam

## Installation on Arch Linux

Build and install the package:

```bash
makepkg -si
```

## Configuration
...

## Default combos
...

## Systemd user service
...

## Documentation

- Installation → `docs/installation.md` 
- Configuration → `docs/configuration.md`  
- Combos → `docs/combos.md` 

## Development

See `docs/roadmap.md` for upcoming improvements and ideas.