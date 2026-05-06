# HMS DICOM Viewer - Setup & Usage Guide

## Overview

The HMS DICOM Viewer is a fully functional medical imaging viewer that:
- ✓ Connects to Orthanc PACS (Picture Archiving and Communication System)
- ✓ Displays DICOM medical images using Cornerstone.js
- ✓ Provides study/series browsing
- ✓ Supports image navigation and basic viewing tools
- ✓ Includes test data with real DICOM samples

## Quick Start

### Option 1: Full Stack (Recommended)
```bash
npm run dev:full
```
This starts everything in the correct order:
- Orthanc PACS (port 8042)
- DICOM Viewer (port 8080)
- Backend API (port 8000)
- Frontend (port 4200)

### Option 2: PACS Only
```bash
npm run dev:pacs
```

### Option 3: Viewer Only
```bash
npm run dev:pacs  # First terminal
npm run dev:viewer  # Second terminal
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **DICOM Viewer** | http://localhost:8080 | View medical images |
| **Orthanc API** | http://localhost:8042 | PACS management & REST API |
| **Orthanc Explorer** | http://localhost:8042/ui/app | Orthanc web interface |
| **Backend API** | http://localhost:8000 | HMS API endpoints |
| **Frontend** | http://localhost:4200 | HMS web application |

## Using the DICOM Viewer

### Navigation
1. **View Studies**: Left sidebar lists all available studies
2. **Search**: Filter patients by name or ID
3. **Load Study**: Click a study to load all images
4. **Navigate Images**: Use Previous/Next buttons to browse
5. **Viewer Tools**: Reset, Fit, and other image controls

### Test Data
The system comes pre-loaded with 4 sample DICOM studies:
- Patient: `CompressedSamples^US1`
- Modality: Ultrasound (US)
- Multiple series available

### Keyboard Controls
- **Arrow Keys**: Navigate between images
- **Mouse Wheel**: Zoom in/out
- **Drag**: Pan across image

## Architecture

```
┌─────────────────────────────────────────┐
│      DICOM Viewer (Port 8080)           │
│  • Cornerstone.js rendering             │
│  • Image navigation & tools              │
└────────────┬────────────────────────────┘
             │ REST API calls
             ↓
┌─────────────────────────────────────────┐
│      Orthanc PACS (Port 8042)           │
│  • DICOM data storage                    │
│  • DICOMweb API (WADO/QidoRs)           │
│  • Docker: jodogne/orthanc:latest      │
└────────────┬────────────────────────────┘
             │ Volume mount
             ↓
┌─────────────────────────────────────────┐
│    orthanc-db (Docker Volume)           │
│  • SQLite database                       │
│  • DICOM binary storage                 │
└─────────────────────────────────────────┘
```

## API Endpoints Used

The viewer communicates with Orthanc via these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/studies` | GET | List all studies |
| `/studies/{id}` | GET | Get study details |
| `/studies/{id}/instances` | GET | Get all instances in study |
| `/instances/{id}/file` | GET | Download DICOM file |

**CORS**: All endpoints have cross-origin headers enabled for browser access.

## Troubleshooting

### Port Already in Use
```bash
npm run kill:ports  # Clear ports 4200, 8000, 8080
```

### Viewer Won't Load
```bash
curl http://localhost:8080  # Check if server running
docker compose -f docker-compose.pacs.yml ps  # Check Orthanc
```

### No Studies Showing
```bash
curl http://localhost:8042/studies | jq .  # Check Orthanc data
npm run test:viewer  # Run system test
```

### View Logs
```bash
docker compose -f docker-compose.pacs.yml logs orthanc
tail -f /tmp/viewer.log
tail -f /tmp/backend.log
```

## Configuration Files

- **Orthanc Config**: `infra/pacs/orthanc.json`
- **Viewer HTML**: `infra/pacs/viewer/index.html`
- **Viewer Server**: `infra/pacs/viewer_server.py`
- **Docker Compose**: `docker-compose.pacs.yml`

## Adding Test Studies

To add more DICOM files:

1. Place `.dcm` files in a directory
2. Use Orthanc API or web interface to upload
3. Or use DICOM client with DIMSE protocol

```bash
# Example: Upload DICOM file to Orthanc
curl -X POST http://localhost:8042/instances \
  -H "Content-Type: application/dicom" \
  --data-binary @path/to/file.dcm
```

## Performance Notes

- Viewer loads full images into memory
- Suitable for workstations with 4GB+ RAM
- Network transmission uses WADO protocol
- Images served from Orthanc directly

## Security Considerations

⚠️ **Current Setup**: Authentication is disabled for development
- Enable auth in production!
- Use HTTPS in production
- Restrict network access
- See `infra/pacs/orthanc.json` for security settings

## Support

For issues:
1. Check Orthanc logs: `npm run dev:pacs:logs`
2. Run tests: `npm run test:viewer`
3. Check browser console for JavaScript errors
4. Verify Orthanc API: `curl http://localhost:8042/studies`

## Next Steps

- [ ] Implement user authentication
- [ ] Add image annotation tools
- [ ] Support for 3D reconstruction
- [ ] DICOM SR (Structured Report) support
- [ ] Mobile responsive design
- [ ] Print functionality
