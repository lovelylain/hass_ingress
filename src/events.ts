import { filter, fromEvent, map, switchMap, take, takeLast, takeUntil, tap } from "rxjs";
import { lockBody, unlockBody } from "./body-lock";
import { isExcluded, toPixelValue } from "./utils";

export interface EdgeSwipeConfig {
  startThreshold: number;
  endThreshold: number;
  preventOthers: boolean;
  lockVerticalScroll: boolean;
  exclusions: string[];
}

export interface BackSwipeConfig {
  threshold: number;
  preventOthers: boolean;
}

export const createEdgeSwipe = ({
  startThreshold,
  endThreshold,
  preventOthers,
  lockVerticalScroll,
  exclusions,
}: EdgeSwipeConfig) =>
  fromEvent<TouchEvent>(document, "touchstart", {
    capture: preventOthers,
  }).pipe(
    filter((event) => !isExcluded(event, exclusions)),
    filter(({ touches: [{ clientX }] }) => clientX < toPixelValue(startThreshold)),
    tap((event) => {
      lockVerticalScroll && lockBody();
      preventOthers && event.stopPropagation();
    }),
    switchMap(({ touches: [{ clientY: startingY }] }) =>
      fromEvent<TouchEvent>(document, "touchmove", {
        capture: preventOthers,
      }).pipe(
        filter(({ touches }) => touches.length < 2),
        tap((event) => preventOthers && event?.stopPropagation()),
        takeUntil(
          fromEvent<TouchEvent>(document, "touchend", {
            capture: preventOthers,
          }).pipe(
            tap((event) => {
              lockVerticalScroll && unlockBody();
              preventOthers && event?.stopPropagation();
            }),
            take(1)
          )
        ),
        takeLast(1),
        map(({ changedTouches: [{ clientX, clientY }] }) => ({
          x: clientX,
          y: clientY,
        })),
        filter(({ x, y }) => x > Math.abs(y - startingY) && x > toPixelValue(endThreshold))
      )
    )
  );

export const createBackSwipe = ({ preventOthers, threshold }: BackSwipeConfig) =>
  fromEvent<TouchEvent>(document, "touchstart").pipe(
    tap((event) => preventOthers && event.stopPropagation()),
    switchMap(({ touches: [{ clientX: startingX }] }) =>
      fromEvent<TouchEvent>(document, "touchend").pipe(
        filter(
          ({ changedTouches: [{ clientX }] }) => startingX - clientX > toPixelValue(threshold)
        ),
        take(1)
      )
    )
  );
