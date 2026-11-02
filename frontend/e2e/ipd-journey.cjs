// Local synthetic journey with IPD notes, medication, transfer, turnover and discharge through the UI.
process.env.HMS_E2E_IPD_UI='1';
process.env.HMS_E2E_ARTIFACTS ||= '/tmp/hms-ipd-browser';
require('./hospital-journey.cjs');
