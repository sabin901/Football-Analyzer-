# Privacy and local storage

The public website is a static GitHub Pages application. It has no application account system, private cloud workspace, analytics collector, advertising cookies or file-upload endpoint.

Public datasets are fetched from the same site. GitHub may process network information such as IP addresses under its own hosting privacy terms. External source links open third-party services only when you choose them. The application does not send imported files to those services.

The analyst workspace reads files you select using your browser. Video uses a temporary local object URL and is not copied into a project backup. Reattach it after reopening. CSV events, notes, project settings and feedback stay in browser memory unless you choose Save on this device or export a file.

Save on this device uses localStorage under footlyzer.analysis.v1. It is not encrypted. Anyone using the same browser profile, and scripts authorized on the same website origin, may access it. GitHub Pages project sites under the same username share an origin; this is not a secure multi-tenant vault. Do not use a shared browser profile for confidential club data. For sensitive material, run the application locally in a dedicated profile or use an organization-approved system.

Remove device copy deletes only this application's saved project key. It does not delete downloaded backups or your source files. New project clears the active in-memory project after confirmation, but leaves an older saved device copy until you save over it or remove it. Clearing browser data may erase saved projects. Keep an exported backup.

Feedback exports contain self-reported time, usefulness, outcome text and event/note counts. Nothing is submitted automatically. Review any exported file before sharing it, especially if you entered confidential names or observations. Video offsets are references, not permission to distribute clips.
