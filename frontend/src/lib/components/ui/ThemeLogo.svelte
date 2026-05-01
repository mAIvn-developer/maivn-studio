<script lang="ts">
  import maivnLogoDark from "$lib/assets/maivn_logo_dark_mode.svg";
  import maivnLogoLight from "$lib/assets/maivn_logo_light_mode.svg";
  import maivnIconDark from "$lib/assets/maivn_icon_dark_mode.svg";
  import maivnIconLight from "$lib/assets/maivn_icon_light_mode.svg";
  import { theme } from "$lib/stores/theme.svelte";

  interface Props {
    icon?: boolean;
    alt?: string;
    class?: string;
  }

  let { icon = false, alt = "mAIvn", class: className = "" }: Props = $props();

  const src = $derived.by(() => {
    if (icon) {
      return theme.resolved === "light" ? maivnIconLight : maivnIconDark;
    }
    return theme.resolved === "light" ? maivnLogoLight : maivnLogoDark;
  });
</script>

<img {src} {alt} class={className} />
