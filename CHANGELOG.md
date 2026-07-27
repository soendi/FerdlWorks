# Changelog

## v1.0.8

- Menüstruktur überarbeitet: Einstellungen + Backup unter Datei
- Neuer Menüpunkt "Rechnungen & Lieferscheine" (Strg+D) mit Dokumentenübersicht
- UI-Redesign: Kunden/Artikel-Dropdowns, Verwaltung-Menü, Doppelklick-Bearbeitung
- Positionstabelle nach unten verschoben, Einheiten erscheinen inline

## v1.0.7

- Iss-Verwaltung: Kunden-, Werkzeug- und Materialdatenbanken mit Treeview + CRUD
- Kombinierte Werkzeug/Material-Suche
- Standard tk.Menü (CTkMenuBar entfernt)
- CI übergibt Version aus version.py an Inno Setup
- AppVerName/VersionInfoVersion/UninstallDisplayName mit korrekter Version

## v1.0.1

- Fixed: GitHub Actions workflow – Icon generation, Inno Setup installation, and release permissions
- Improved: Build pipeline reliability

## v1.0.0

- Initial release
- Invoice (RG) and delivery note (LS) creation with sequential numbering
- Customer, tool, and material databases with CRUD dialogs
- PDF generation with ReportLab
- Email sending via SMTP
- Cloud backup to Google Drive and OneDrive
- Auto-update via GitHub Releases
- Password-protected login
- Customizable settings (sender address, VAT, printer, etc.)
