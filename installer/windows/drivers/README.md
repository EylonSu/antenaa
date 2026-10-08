# Windows USB serial drivers

The installer bundles two vendor drivers so clone Arduino boards work out of the box.
Genuine Arduino boards use the built-in Windows `usbser` driver and need nothing.
The driver files are **not committed**; they are downloaded at build time.

| Folder      | Driver                         | Official source |
|-------------|--------------------------------|-----------------|
| `CH341SER/` | WCH CH340/CH341 (`CH341SER.INF`) | https://www.wch-ic.com/downloads/CH341SER_ZIP.html (file `CH341SER.ZIP`) |
| `FTDI/`     | FTDI CDM VCP driver (`ftdibus.inf`, `ftdiport.inf`) | https://ftdichip.com/drivers/vcp-drivers/ ("Windows (Desktop)" zip, e.g. `CDM212364_Setup.zip` or the "available as setup executable" CDM zip) |

## Automated download

```powershell
pwsh installer/windows/drivers/fetch_drivers.ps1
```

The script downloads both zips and extracts them so that the layout is:

```
drivers/CH341SER/CH341SER.INF (+ .SYS/.CAT)
drivers/FTDI/*.inf (+ .sys/.cat, amd64/ etc.)
```

URLs can be overridden with `-Ch341Url` / `-FtdiUrl` (or the `CH341_URL` / `FTDI_URL`
environment variables) when the vendors move files. If the FTDI download is only an
installer `.exe`, extract it with 7-Zip (`7z x CDM*.exe -oFTDI`) – it is a self-extracting archive
containing the INF files.

`setup.iss` runs `pnputil /add-driver <inf> /install` for each, silently and with admin rights.
If a folder is missing, that driver step is skipped.
