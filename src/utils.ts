type Node = Document | Element | null;

// Adapted from https://www.abeautifulsite.net/posts/querying-through-shadow-roots/
export function shadowQuery(selector: string, rootNode: Node = document): HTMLElement | null {
  // Return early if explicit null passed
  if (rootNode === null) return null;

  const selectors = String(selector).split(">>>");
  let currentNode: Node = rootNode;

  selectors.find((_, index) => {
    if (index === 0) {
      currentNode = rootNode.querySelector(selectors[index]);
    } else if (currentNode instanceof Element) {
      currentNode = (currentNode?.shadowRoot ?? currentNode).querySelector(selectors[index]);
    }

    return currentNode === null;
  });

  if (currentNode === rootNode) {
    return null;
  }

  return currentNode as HTMLElement | null;
}

export function toPixelValue(value: number): number {
  return value > 1 ? value : window.innerWidth * value;
}

export const isExcluded = (event: TouchEvent, exclusions: string[]) =>
  exclusions.length &&
  event.composedPath().some((el) => el instanceof Element && el.matches(exclusions.join()));
