export function shouldShowScrollToBottom(container: HTMLDivElement, threshold: number): boolean {
  const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
  return distanceFromBottom > threshold;
}

export function scrollContainerToBottom(container: HTMLDivElement): void {
  container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
}

export function jumpContainerToBottom(container: HTMLDivElement): void {
  container.scrollTop = container.scrollHeight;
}
