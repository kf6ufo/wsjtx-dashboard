# Current rebuild checkpoint

October 23, 2026. Branch `rebuild/step-1`. The operator reviewed and accepted Step 0 and requested Step 1. Step 0 is preserved at branch `rebuild/step-0`, commit `3d2f9a61b2e255df12d1deb605d72b1fd202c8d3`; its evidence is [archived](checkpoint-step0.md). All prior history remains intact.

Step 1 implementation/validation is in progress. See [Step 1 operation and behavior](step-1.md). The new primary receiver is passive and configurable; no Wavelog/QRZ credentials, QSO submissions, forwarding or radio commands. Keep all production station services running unchanged. Stop for Step 1 review before Step 2.

Initial offline checks: 36 Python cases passed, including isolated real loopback UDP reception and receiver restart. Clean native installation, browser acceptance, upgrade and actual station multicast evidence will be recorded after verification. Ubuntu execution remains untested.

GitHub publication remains pending explicit authorization after the previous automatic approval rejection; no new push is attempted by this step. Local branch installation is available.
