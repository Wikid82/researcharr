# Project Roadmap

The roadmap is now maintained in the project wiki for easier updates and collaboration. The wiki roadmap was recently reprioritized to emphasize core processing, reliability, and API/worker improvements before UI polish.

**See:** [Project Roadmap (Wiki)](../researcharr.wiki/Roadmap.md)
 
Note: the roadmap includes plans for release-aware processing: withhold processing of newly released files for a configurable window (default: 7 days) and skip items with no release date by default.
 
Planned: add a notifications layer (webhooks + popular services). Discord is a priority; consider Apprise for broad service support.


Packaging & Distribution:
- Once a working test suite and CI are in place, begin releasing native packages (outside Docker) for common OSes:
	- Linux: DEB packages (Debian/Ubuntu) and optional AppImage/Flatpak for wider distro support.
	- Windows: EXE/MSI installers for easy installation on servers and desktops.
	- macOS: PKG or Homebrew formula / notarized app where appropriate.
	- Ensure reproducible builds, signing (when feasible), and documentation for running as a service (systemd, Windows Service, launchd).

