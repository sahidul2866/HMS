# OPD workflow and PA operation

## Patient flow

1. Book an appointment for an available doctor slot, then check it in from Appointments. Walk-in registration also creates an OPD visit and serial. Cancelled appointments cannot be checked in, and check-in cannot create a second visit.
2. Open **OPD → Doctor Serials & PA**. Choose the doctor and, when configured, their room/counter. Each doctor has an independent daily sequence; the token label includes a stable doctor identifier to avoid collisions between similar doctor names/codes.
3. **Call Next**, **Call**, **Announce Again**, **Skip**, **Recall**, and **No Show** manage arrivals. **Start** marks the serial in progress; **Open Consultation** opens its prescription. The visit list’s **Start Visit** starts and opens the consultation directly. Payment is tracked separately and does not overwrite the clinical state.
4. Save clinical notes, medicines, and investigations. **Finalize Prescription** saves the submitted clinical fields and closes the doctor’s serial in one transaction. The configured auto-call policy can call the next waiting patient. Repeating finalization does not advance the queue again. Other fields already on the consultation, such as past history, remain intact when omitted from a partial update.
5. Print the saved prescription. Long prescriptions can flow onto additional pages. Unsaved clinical edits prompt before closing, navigation, or browser unload.
6. Open billing from the visit. Invoice payments, partial payments, and refunds update the OPD payment status while preserving the consultation status. Multiple receipts created in the same second have distinct identifiers. A billed visit must belong to the invoice’s patient.
7. **Convert to IPD** prefills the patient, doctor, and clinical context. Admission, OPD linkage, and queue completion commit together. Failed handoffs roll back together, and repeated conversion is rejected. The recorded diagnosis and doctor are retained when omitted from the conversion request.

Only waiting visits can be reassigned/rescheduled. Reassignment moves the serial to the destination doctor. Transfer to another service creates a separate destination token and retains the original OPD serial.

## PA computer setup

Connect the queue-display computer’s audio output to the PA audio input. Sign in with access to the required OPD queues, open **Doctor Serials & PA**, and select **Display Screen**. A doctor account is restricted to its own queue; use an appropriately authorized reception/display account for a hospital-wide board.

On that computer, select **Enable PA audio**, then **Test PA**. Confirm that sound is audible in the actual waiting area. Keep only one receiver enabled per PA zone to avoid duplicate audio. The display polls fresh queue data every five seconds; operational queue responses and slot availability are excluded from offline/light-view caching. The browser must stay open and active; browser background throttling can delay polling.

Doctor actions are recorded on the server. The enabled display announces new call timestamps with the serial number and doctor/room, without speaking the patient’s name. **Announce Again** updates the call timestamp for an intentional repeat. Existing calls are not replayed when audio is enabled, and calls older than two minutes are ignored. The board displays all current doctor serials in its selected scope.

PA speech prefers Azure neural voices: `en-US-JennyNeural` for English and `bn-BD-NabanitaNeural` for Bangla. Add `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` to `backend/.env`, restart the backend, and re-enable PA audio. Keys remain on the backend. The authenticated `/api/v1/queue/speech` endpoint converts short announcements to MP3; it escapes SSML, limits request length and frequency, and keeps a bounded 15-minute in-memory audio cache for repeats. Announcements play sequentially, and disabling PA cancels pending requests/playback and releases audio URLs.

The PA status identifies the active engine. If Azure is unconfigured, unreachable, or fails, the device speech engine is used with a visible fallback label. Bangla fallback requires an installed Bangla voice. Queue sound checks and calls send their announcement text (serial number, doctor/room) to Azure; patient names are not included. Browser sound permissions, the computer output device, PA amplifier volume, and the physical cable remain part of the site setup. Without Azure credentials, provider requests can only be verified with mocked responses; live neural synthesis and physical PA audibility need a configured Azure subscription and a site sound check.

Azure API reference: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech
Voice support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support

## Verification

Run the frontend checks from the repository root:

```sh
npm run build --prefix frontend
npm test --prefix frontend -- --watch=false --browsers=ChromeHeadless
```

For database integration tests, provision a disposable local PostgreSQL database whose name contains `test`, then run with its URL explicitly configured:

```sh
PYTHONPATH=backend DATABASE_URL=postgresql://localhost/hms_test HMS_TEST_DATABASE_URL=postgresql+psycopg://localhost/hms_test SECRET_KEY=local-opd-tests backend/.venv/bin/python -m pytest backend/tests -q
```

The integration suite creates and removes isolated random schemas, uses synthetic patient data, rejects remote database targets, and includes concurrent independent database sessions. It exercises the full HTTP appointment-to-prescription-to-payment-to-IPD flow as well as service-level lifecycle, doctor isolation, payment/refund, duplicate booking/check-in, reassignment, transfer, and rollback cases. Angular tests cover consultation controls, dirty-form protection, prescription HTML, and PA announcement deduplication/repeat/disable behavior. Physical PA audibility and full manual screen-by-screen acceptance remain site checks.
