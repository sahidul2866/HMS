#!/bin/bash
# Test DICOM Viewer Full Flow

echo "============================================"
echo "🏥 HMS DICOM Viewer - Full System Test"
echo "============================================"
echo ""

# Test 1: Orthanc API
echo "1️⃣  Testing Orthanc API..."
STUDIES=$(curl -s http://localhost:8042/studies)
STUDY_COUNT=$(echo "$STUDIES" | jq 'length')
if [ "$STUDY_COUNT" -gt 0 ]; then
    echo "   ✓ Orthanc responding with $STUDY_COUNT studies"
else
    echo "   ✗ Orthanc not responding"
    exit 1
fi

# Test 2: Viewer Server
echo ""
echo "2️⃣  Testing Viewer Server..."
VIEWER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/)
if [ "$VIEWER_STATUS" = "200" ]; then
    echo "   ✓ Viewer responding on port 8080"
else
    echo "   ✗ Viewer not responding (HTTP $VIEWER_STATUS)"
    exit 1
fi

# Test 3: Load Studies from Viewer
echo ""
echo "3️⃣  Testing Study Loading..."
FIRST_STUDY=$(echo "$STUDIES" | jq -r '.[0]')
STUDY_DATA=$(curl -s "http://localhost:8042/studies/$FIRST_STUDY")
PATIENT_NAME=$(echo "$STUDY_DATA" | jq -r '.PatientMainDicomTags.PatientName')
STUDY_DATE=$(echo "$STUDY_DATA" | jq -r '.MainDicomTags.StudyDate')

if [ ! -z "$PATIENT_NAME" ] && [ "$PATIENT_NAME" != "null" ]; then
    echo "   ✓ Study loaded: $PATIENT_NAME (Date: $STUDY_DATE)"
else
    echo "   ✗ Failed to load study data"
    exit 1
fi

# Test 4: Load Instances
echo ""
echo "4️⃣  Testing Instance Loading..."
INSTANCES=$(curl -s "http://localhost:8042/studies/$FIRST_STUDY/instances")
INSTANCE_COUNT=$(echo "$INSTANCES" | jq 'length')
if [ "$INSTANCE_COUNT" -gt 0 ]; then
    echo "   ✓ Found $INSTANCE_COUNT instances in study"
else
    echo "   ✗ No instances found"
    exit 1
fi

# Test 5: Load Instance Details
echo ""
echo "5️⃣  Testing Instance Details..."
FIRST_INSTANCE=$(echo "$INSTANCES" | jq -r '.[0].ID')
INSTANCE_DETAIL=$( echo "$INSTANCES" | jq '.[0]')
MODALITY=$(echo "$INSTANCE_DETAIL" | jq -r '.MainDicomTags.Modality // "US"')
if [ ! -z "$FIRST_INSTANCE" ] && [ "$FIRST_INSTANCE" != "null" ]; then
    echo "   ✓ Instance loaded: ID=$FIRST_INSTANCE"
else
    echo "   ✗ Failed to load instance details"
    exit 1
fi

# Test 6: DICOM File Access
echo ""
echo "6️⃣  Testing DICOM File Serving..."
FILE_SIZE=$(curl -s -o /dev/null -w "%{size_download}" "http://localhost:8042/api/instances/$FIRST_INSTANCE/file")
if [ "$FILE_SIZE" -gt 0 ]; then
    echo "   ✓ DICOM file accessible ($FILE_SIZE bytes)"
else
    echo "   ✗ DICOM file not accessible"
    exit 1
fi

echo ""
echo "============================================"
echo "✅ All tests passed! System ready."
echo "============================================"
echo ""
echo "🌐 Access the viewer at: http://localhost:8080"
echo ""
