# Android-to-backend local development

The Android app gets its backend configuration from one Gradle property:
`BACKEND_BASE_URL`. Its default is `http://10.0.2.2:8000/`, the special Android
Emulator address for a server listening on the development laptop. It is not a
LAN address and will not work from a physical phone.

The temporary backend endpoint also requires an existing PostgreSQL user's UUID.
Supply it only on your local machine as `BACKEND_DEVELOPMENT_USER_ID`; do not
commit a real user ID into this repository.

## Android Emulator

Start FastAPI so it listens beyond loopback:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The emulator's `localhost` is the emulator itself. Use the default
`http://10.0.2.2:8000/` mapping for the laptop backend.

```powershell
.\gradlew.bat :app:assembleDebug `
  -PBACKEND_BASE_URL=http://10.0.2.2:8000/ `
  -PBACKEND_DEVELOPMENT_USER_ID=EXISTING-POSTGRES-USER-UUID
```

## Physical Android device

Connect the phone and laptop to the same network. Run FastAPI with
`--host 0.0.0.0`, allow the port through the Windows firewall if required, and
substitute the laptop's current LAN IP in the build property:

```powershell
.\gradlew.bat :app:assembleDebug `
  -PBACKEND_BASE_URL=http://192.168.x.x:8000/ `
  -PBACKEND_DEVELOPMENT_USER_ID=EXISTING-POSTGRES-USER-UUID
```

Use a real HTTPS backend URL for release builds. The debug manifest permits
cleartext HTTP solely for local FastAPI development.
