// Auto-select the "Bookmarked" chip when the ComfyUI v2 node search opens.
//
// The frontend hardcodes the default category (NodeSearchContent.vue,
// selectedCategory = 'most-relevant') with no setting to change it. The chip
// renders as [data-testid="search-category-favorites"] with aria-pressed="true"
// when active, and only exists if at least one node is bookmarked.
//
// Only newly inserted chips are clicked (childList mutations, never attribute
// changes), so deselecting the chip by hand does not re-trigger this.
import { app } from "../../scripts/app.js";

const CHIP_SELECTOR = '[data-testid="search-category-favorites"]';

function findChip(node) {
    if (!(node instanceof Element)) return null;
    if (node.matches(CHIP_SELECTOR)) return node;
    return node.querySelector(CHIP_SELECTOR);
}

app.registerExtension({
    name: "rubytools.autobookmarks",
    setup() {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const added of mutation.addedNodes) {
                    const chip = findChip(added);
                    if (!chip) continue;
                    if (chip.getAttribute("aria-pressed") !== "true") chip.click();
                    return;
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
});
