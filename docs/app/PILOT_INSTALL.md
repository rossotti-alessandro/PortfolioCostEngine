# FeeLens pilot install: one office machine, real client data

Story SC-11.6. Kit: [`deployment/local/`](../../deployment/local/). Gates: [READINESS.md](../READINESS.md) G3 to G9.
Engineering instructions, not legal advice: the DPIA, consent text and retention period are Safe Capital's
decisions (READINESS.md section 7).

**Recommended path.** Start on one machine in the Safe Capital office, reachable only from the office
network. Move to a Swiss host the firm controls only when more people or remote access are needed
(section 7). The Render demo never receives client documents.

Tested on 2026-11-13 in a container: the kit built, served HTTPS through Caddy, the first admin was created
with the command line, finished setup with an authenticator code, uploaded and erased a SYNTHETIC
statement, and an encrypted backup was restored into a fresh data folder with the accounts intact.

## 1. The machine

| Need | Why |
|---|---|
| A dedicated computer (mini PC or desktop), 4+ cores, 16 GB RAM, 256 GB SSD | OCR of scanned statements is CPU-bound |
| Full-disk encryption on: LUKS (choose "encrypt" in the Ubuntu 24.04 LTS installer), FileVault (Mac) or BitLocker (Windows) | A stolen machine must not expose documents (FADP art. 8, data security) |
| Ubuntu 24.04 LTS with Docker Engine (recommended), or Docker Desktop on Mac or Windows | One supported setup, automatic security updates (`unattended-upgrades`) |
| Office network only. No port forwarding on the router. Remote use only through the firm's VPN | Nothing from the internet can reach the app |
| A second encrypted disk or a NAS share for backups, and a place offline for the backup key (a USB key in the safe) | A backup that sits next to its key protects nothing |
| Screen lock after 5 minutes, separate OS accounts, no shared login | Professional secrecy (FinIA art. 69) applies to the whole machine |

## 2. Install

```bash
sudo git clone https://github.com/rossotti-alessandro/portfoliocostengine.git /opt/feelens
cd /opt/feelens/deployment/local   # private repository: clone with a read-only GitHub token
cp .env.example .env
chmod 600 .env
openssl rand -base64 48        # paste as PCE_SECRET_KEY in .env
age-keygen -o backup-key.txt   # copy the "public key" line into BACKUP_RECIPIENT in .env,
                               # then move backup-key.txt OFF this machine (USB key in the safe)
```

In `.env` set `PCE_ADMIN_TENANT` (the firm id, e.g. `safe-capital`), `FEELENS_HOST` (the name analysts
type, e.g. `feelens.safecapital.local`, added to the office DNS or each computer's hosts file) and
`PCE_RETENTION_DAYS` (Safe Capital's decision; 90 is a placeholder). Leave the break-glass admin lines
empty.

```bash
docker compose up -d --build   # first build takes 5 to 10 minutes
docker compose ps              # feelens and caddy "running"
```

The compose file fixes the safe settings: sign-in with an authenticator app required (`PCE_REQUIRE_MFA=1`),
secure cookies, no demo data, no outside AI (`PCE_ALLOW_EXTERNAL_AI=false`), the app reachable only through
Caddy on port 443.

**HTTPS certificate.** Caddy makes its own certificate authority. Install
`caddy/caddy/pki/authorities/local/root.crt` once on each analyst's computer as a trusted root
(Windows: double-click → Install → Local Machine → Trusted Root; Mac: Keychain Access → System → Always
Trust). With a public DNS name and a real certificate, remove the `tls internal` line from `Caddyfile`.

## 3. First admin and the other accounts

```bash
./feelens.sh users create massimo --tenant safe-capital --role senior --role analyst --admin
```

It prints a one-time password once. Give it to the person directly (in person or by phone, never by
email or chat). At the first sign-in on `https://<FEELENS_HOST>` the person:

1. signs in with the username and one-time password;
2. chooses their own password (12+ characters);
3. scans the QR link or types the setup key into an authenticator app (Microsoft Authenticator, Google
   Authenticator, 1Password, Bitwarden: any TOTP app; no Microsoft 365 needed);
4. types the 6-digit code. From now on every sign-in asks for password and code.

Until those steps are done the account can reach nothing but account setup. After that, admins add
everyone else from **Users** in the app (one account per person, never shared). The same page resets a
lost phone or password (new one-time password, all sessions end), signs a person out everywhere, and
disables a leaver's account the same day. Admins cannot disable or reset themselves, so keep two admins.

Command-line equivalents: `./feelens.sh users list|reset|disable|enable <username> --tenant safe-capital`.

## 4. Backups (daily) and restore test (quarterly)

```bash
sudo crontab -e
# 02:00 backup, 03:00 retention
0 2 * * * /opt/feelens/deployment/local/backup.sh /mnt/backup/feelens >> /var/log/feelens-backup.log 2>&1
0 3 * * * /opt/feelens/deployment/local/feelens.sh retention >> /var/log/feelens-retention.log 2>&1
```

- `backup.sh` takes a consistent copy of the database and the stored documents and encrypts it with the
  age public key before it touches the backup folder. It keeps 30 days; older backups are deleted.
  An erased prospect therefore disappears from backups within 30 days: the DPIA and the deletion
  confirmation to the prospect must say so.
- `restore.sh <file> <backup-key.txt>` stops the app, keeps the current data aside, restores, restarts.
  Every quarter, restore the latest backup on a spare machine and sign in. Record the date: a backup that
  was never restored is not a backup.
- age: <https://age-encryption.org> (BSD-3-Clause), `apt install age`.

## 5. Retention and deletion

- `./feelens.sh retention --dry-run` lists prospects with no activity for `PCE_RETENTION_DAYS` days that did
  not become clients (CRM stage "won"); without `--dry-run` it erases them. Output is ids and counts only.
- On a prospect's request an admin erases the prospect from the Prospects list (bin icon): pick the reason,
  optionally delete the CRM contact, type the prospect code. Documents, extracted figures, reviews,
  proposals and earlier log entries go; one log entry with the reason and counts stays as proof.

## 6. What is logged

Each sign-in, failed authenticator code, prospect opened, document viewed, change, export and deletion is
logged with user, time and ids, never file contents or names. Log entries cannot be edited (database
trigger). The web server log keeps request paths, including the prospect code typed to confirm a deletion:
use codes like `P-1042`, never a person's name, as the prospect code.

## 7. Later: a Swiss host

When the pilot needs remote access or more users: a Swiss-owned provider with Swiss data centres
(for example Infomaniak, Geneva, or Exoscale, Geneva and Zurich zones), a small VM with an encrypted
volume, the same kit, a real DNS name with a public certificate, SSH by key only, firewall open on 443
only, and a signed processing agreement with the provider (FADP art. 9). Postgres and single sign-on
come with SC-11.2.

## 8. Before the first real document

Tick every gate in [READINESS.md](../READINESS.md) section 2. The engineering gates G4 to G7 close with
this kit; G3 (where it runs) and G9 (DPIA, consent text, processing record, compliance sign-off) need
Safe Capital's decision and signature.
