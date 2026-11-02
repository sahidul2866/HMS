# Application UI states

The root app mounts `AppStateComponent` for connection status, action feedback, and same-account session recovery. HTTP loading uses non-blocking skeletons, an indeterminate progress bar, pending-request count, and elapsed time. After eight seconds users can select a lighter view. It disables animations and uses previously loaded responses when available; “Use live data” exits it. In-place loading messages also include skeletons and honor reduced-motion preferences.

Empty and filtered-list states explain what creates the content or suggest spelling, shorter search terms, and broader filters. Shared autocomplete offers a clear-search action when no option matches.

HTTP failures explain recovery for connection failures, access denial, rate limiting, and server errors. Permission guards explain the required access and send users to their available profile. Action feedback is rendered globally, with dismiss buttons, accessible announcements, longer error visibility, and success messages that indicate the next step. Specific workflows can pass a second argument to `NotificationService.success` to supply their own next step.

The offline interceptor caches up to 100 successful authenticated JSON GET responses in memory for the current tab. Cached responses are labelled with their timestamp. Account changes and successful writes invalidate this cache; requests already in flight cannot populate another account’s cache. It never queues writes. Offline work covers records already loaded and edits in open forms. It does not support offline reload, first-time searches, saving, or payments. Forms and cache are not persisted by this feature.

Rejected refresh tokens open a modal without clearing tabs, component state, or form values. Reauthentication must use the same account. Password failures keep the dialog open. Network failures during refresh do not clear the session. Failed actions are not automatically resubmitted; users review and submit again. Reloading or explicitly discarding work can still lose unsaved edits.

Submitted invalid forms focus the first invalid field and provide linked field messages, invalid styling, and a summary. Native constraints provide specific correction guidance; custom Angular validators retain their field requirements and existing messages.

Verification:

- `npm run build --prefix frontend`
- `npm test --prefix frontend -- --watch=false --browsers=ChromeHeadless`

Tests cover cached reads, blocked offline writes, account isolation (including in-flight responses), mutation invalidation, lighter-view refresh, rejected versus unreachable token refresh, account checks during reauthentication, modal password failures, and linked field validation.
