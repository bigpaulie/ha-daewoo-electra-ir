# Privacy

The integration uses the selected Home Assistant entities and the existing Broadlink integration locally. It adds no analytics, cloud account, telemetry, background internet requests, or credentials. HACS and Home Assistant retain their own normal network behavior, including GitHub checks for repository updates.

Entity selections and options are stored by Home Assistant in its config entry. Requested climate state and diagnostic attributes can be stored by the recorder according to the instance's configuration. Existing Broadlink infrastructure handles learned codes and its own normal send metadata. None of these local settings are uploaded by this integration.

The public source includes anonymized IR regression fixtures. The IR frames contain protocol settings, not Broadlink MAC/IP addresses, authentication tokens, household entity names, or source-chat URLs. No personal entity defaults are shipped. Every installation selects its own remote and sensor; learned fallbacks use explicitly entered mappings.

Before sharing logs or issue reports, remove entity IDs, local paths, IP/MAC addresses, account information, and any tokens. Do not upload Home Assistant `.storage` files, backups, secrets files, or complete environment dumps.

The repository's publication check scans source and distributable contents for common private-data patterns and excludes caches/local files. Pattern scanning reduces accidental disclosure; it is not a guarantee that arbitrary future contributions contain no personal information. Review changes before publication.
