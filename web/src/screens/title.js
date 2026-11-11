/**
 * Archival Title Screen - Quiet Bastion Design System.
 * Warm paper ground, clean editorial layout, single black action button.
 */

export function createTitleScreen({ onPlay }) {
  const el = document.createElement('div');
  el.className = 'flex flex-col min-h-screen w-full bg-surface text-on-surface';

  el.innerHTML = `
    <!-- Top Bar -->
    <header class="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-md pt-safe border-b border-surface-container-highest">
      <div class="h-14 max-w-[480px] mx-auto px-margin flex items-center justify-between">
        <span class="font-label-lg text-label-lg uppercase tracking-wider text-on-surface font-semibold">QUORIDOR</span>
        <span class="font-label-sm text-label-sm text-outline font-mono">V2.0</span>
      </div>
    </header>

    <main class="flex-1 flex flex-col items-center justify-center pt-16 pb-safe px-margin">
      <div class="w-full max-w-[420px] flex flex-col gap-space-lg text-center items-center py-space-xl">
        
        <!-- Minimalist Icon / Board Symbol -->
        <div class="w-16 h-16 rounded-2xl bg-surface-container border border-surface-container-highest flex items-center justify-center shadow-sm">
          <div class="grid grid-cols-2 gap-1.5 p-2.5">
            <div class="w-3.5 h-3.5 rounded-full bg-secondary"></div>
            <div class="w-3.5 h-3.5 rounded-sm bg-primary"></div>
            <div class="w-3.5 h-3.5 rounded-sm bg-primary"></div>
            <div class="w-3.5 h-3.5 rounded-full bg-on-tertiary-container"></div>
          </div>
        </div>

        <!-- Typography Headline -->
        <div class="flex flex-col gap-space-xs">
          <h1 class="font-headline-lg text-headline-lg font-bold tracking-tight text-on-surface">QUORIDOR</h1>
          <p class="font-body-md text-body-md text-on-surface-variant max-w-xs mx-auto">
            The abstract strategy game of corridors and barriers.
          </p>
        </div>

        <!-- Editorial Feature Cards -->
        <div class="w-full flex flex-col gap-space-xs text-left bg-surface-container-lowest p-space-md rounded-xl border border-surface-container-highest shadow-sm">
          <div class="flex items-start gap-space-sm p-space-xs">
            <span class="material-symbols-outlined text-secondary text-[20px] shrink-0 mt-0.5">psychology</span>
            <div class="flex flex-col">
              <span class="font-body-md text-body-md font-semibold text-on-surface">Intelligent Opponents</span>
              <span class="font-body-sm text-body-sm text-on-surface-variant">Challenge Wobbles, Dash, Professor Prune, and The Gambler.</span>
            </div>
          </div>
          <div class="h-[1px] bg-surface-container-highest w-full my-0.5"></div>
          <div class="flex items-start gap-space-sm p-space-xs">
            <span class="material-symbols-outlined text-on-tertiary-container text-[20px] shrink-0 mt-0.5">route</span>
            <div class="flex flex-col">
              <span class="font-body-md text-body-md font-semibold text-on-surface">Corridor Analysis</span>
              <span class="font-body-sm text-body-sm text-on-surface-variant">Real-time shortest path visualization, wall preview, and telemetry.</span>
            </div>
          </div>
        </div>

        <!-- Single Primary Action -->
        <div class="w-full flex flex-col gap-space-sm pt-space-xs">
          <button id="btn-play" type="button" class="w-full py-3.5 px-space-md rounded bg-primary text-on-primary font-headline-sm text-headline-sm font-medium tracking-wide hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-space-xs cursor-pointer shadow-sm">
            <span>Play vs AI</span>
            <span class="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
          <p class="font-label-sm text-label-sm text-outline">Press [Space] or [Enter] to begin</p>
        </div>

      </div>
    </main>
  `;

  el.querySelector('#btn-play')?.addEventListener('click', () => {
    onPlay();
  });

  return el;
}
