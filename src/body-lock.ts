import {shadowQuery} from './utils'

interface OverrideConfig {
  onLock?: () => void
  onUnlock?: () => void
}

const overrides = {
  haPanelEnergy: {
    onLock: () => {
      const header = shadowQuery(
        'home-assistant >>> home-assistant-main >>> ha-drawer ha-panel-energy >>> ha-top-app-bar-fixed >>> header'
      )

      // Energy panel has fixed position but no coordinates by default
      if (header) {
        header.style.top = '0px'
      }
    },
  },
}

export function lockBody() {
  Object.assign(document.body.style, {
    position: 'fixed',
    inset: 0,
    top: `-${document.documentElement.scrollTop}px`,
  })

  Object.values(overrides).forEach(({onLock}: OverrideConfig) => onLock?.())
}

export function unlockBody() {
  const top = Math.abs(parseInt(document.body.style.top)) || document.documentElement.scrollTop

  Object.assign(document.body.style, {
    position: '',
    inset: '',
  })

  window.scrollTo({top, left: 0, behavior: 'auto'})

  Object.values(overrides).forEach(({onUnlock}: OverrideConfig) => onUnlock?.())
}
