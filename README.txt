═══════════════════════════════════════════════════════════════════════
  QUINIX 6-WORKER SYSTEM - INSTRUKTIONER
═══════════════════════════════════════════════════════════════════════

🎯 FORMÅL:
Kør scriptet i 6 browser vinduer samtidig for 6x hastighed!
Hver worker arbejder på forskellige dele af listen, så de ALDRIG kolliderer.

═══════════════════════════════════════════════════════════════════════

📋 TRIN-FOR-TRIN GUIDE:

1️⃣ ÅBEN 6 BROWSER VINDUER
   - Åben Quinyx absence request siden i 6 separate vinduer/tabs
   - Arrangér dem så du kan overskue dem alle (f.eks. 3x2 grid)

2️⃣ PASTE SCRIPTS I HVERT VINDUE:

   VINDUE 1:
   ✓ Åben Console (F12)
   ✓ Kopiér ALT fra: worker-1-top.txt
   ✓ Paste i console
   ✓ Tryk Enter
   → Worker starter fra request #1 (toppen)

   VINDUE 2:
   ✓ Åben Console (F12)
   ✓ Kopiér ALT fra: worker-2-sixth1.txt
   ✓ Paste i console
   ✓ Tryk Enter
   → Worker starter ved position ~#1984 (1/6)

   VINDUE 3:
   ✓ Åben Console (F12)
   ✓ Kopiér ALT fra: worker-3-third.txt
   ✓ Paste i console
   ✓ Tryk Enter
   → Worker starter ved position ~#3968 (2/6 = 1/3)

   VINDUE 4:
   ✓ Åben Console (F12)
   ✓ Kopiér ALT fra: worker-4-half.txt
   ✓ Paste i console
   ✓ Tryk Enter
   → Worker starter ved position ~#5952 (3/6 = midten)

   VINDUE 5:
   ✓ Åben Console (F12)
   ✓ Kopiér ALT fra: worker-5-twothird.txt
   ✓ Paste i console
   ✓ Tryk Enter
   → Worker starter ved position ~#7936 (4/6 = 2/3)

   VINDUE 6:
   ✓ Åben Console (F12)
   ✓ Kopiér ALT fra: worker-6-bottom.txt
   ✓ Paste i console
   ✓ Tryk Enter
   → Worker starter fra request #11903 (bunden)

3️⃣ LEAN BACK!
   → Alle workers starter automatisk efter 3 sekunder
   → Se dem arbejde parallelt! ✨

═══════════════════════════════════════════════════════════════════════

📊 HVORDAN DET VIRKER:

Med 11903 requests fordelt på 6 workers:

┌────────────────────────────────────────────┐
│  Request #1        ← WORKER 1 (TOP)        │
│  ...                                       │
│  Request #1984     ← WORKER 2 (1/6)        │
│  ...                                       │
│  Request #3968     ← WORKER 3 (1/3)        │
│  ...                                       │
│  Request #5952     ← WORKER 4 (MIDTEN)     │
│  ...                                       │
│  Request #7936     ← WORKER 5 (2/3)        │
│  ...                                       │
│  Request #11903    ← WORKER 6 (BOTTOM)     │
└────────────────────────────────────────────┘

Hver worker tager sin egen "zone" så de ALDRIG kolliderer!
Når listen skrumper, justerer de automatisk deres position.

═══════════════════════════════════════════════════════════════════════

⚡ FORVENTET HASTIGHED:

Enkelt worker:  ~6-7 timer for 11903 requests
Med 6 workers:  ~1-1.5 timer for 11903 requests

HASTIGHED OP 5-6X! 🚀🚀🚀

═══════════════════════════════════════════════════════════════════════

⚠️ VIGTIGT:

✓ Hver worker SKAL køre sit eget script (worker-1 til worker-6)
✓ Luk IKKE vinduer før de er færdige
✓ Hvis et vindue crasher: refresh og paste samme script igen
✓ Hver worker har separate counters:
  • window.WORKER1_TOPDeletedCount
  • window.WORKER2_SIXTH1DeletedCount
  • window.WORKER3_THIRDDeletedCount
  • window.WORKER4_HALFDeletedCount
  • window.WORKER5_TWOTHIRDDeletedCount
  • window.WORKER6_BOTTOMDeletedCount

═══════════════════════════════════════════════════════════════════════

🛑 FOR AT STOPPE:

→ Refresh siden (F5) i det vindue du vil stoppe
→ Eller refresh alle vinduer for total stop

═══════════════════════════════════════════════════════════════════════

💡 TIPS:

✓ Hver worker logger sit WORKER_ID i console
✓ Hold øje med "[WORKER1_TOP]", "[WORKER2_SIXTH1]" osv. i logs
✓ Du kan se status for hver worker individuelt i deres console
✓ Hvis én worker går stærkere end de andre, er det OK - de kolliderer ikke!

═══════════════════════════════════════════════════════════════════════

🎯 QUICK START (COPY/PASTE):

1. Åben 6 tabs på Quinyx
2. I hver tab: F12 → Console
3. Tab 1: Paste worker-1-top.txt og Enter
4. Tab 2: Paste worker-2-sixth1.txt og Enter
5. Tab 3: Paste worker-3-third.txt og Enter
6. Tab 4: Paste worker-4-half.txt og Enter
7. Tab 5: Paste worker-5-twothird.txt og Enter
8. Tab 6: Paste worker-6-bottom.txt og Enter
9. Vent 3 sekunder...
10. Done! 🎉

═══════════════════════════════════════════════════════════════════════

HELD OG LYKKE MED DINE 11903 REQUESTS! 💪
