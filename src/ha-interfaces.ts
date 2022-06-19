export interface SidebarSwipeConfig {
  start_threshold?: number
  end_threshold?: number
  back_threshold?: number
  prevent_others?: boolean
  lock_vertical_scroll?: boolean
  exclusions?: string[]
}

interface Lovelace {
  config: {sidebar_swipe: SidebarSwipeConfig | undefined} | undefined
}

export interface HaPanelLovelace extends HTMLElement {
  lovelace: Lovelace | undefined
}
