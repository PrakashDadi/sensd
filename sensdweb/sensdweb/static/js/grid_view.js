document.addEventListener("DOMContentLoaded", () => {
    const search = document.getElementById("tool-search");
    const cards = Array.from(document.querySelectorAll(".analysis-card"));
    const filters = Array.from(document.querySelectorAll(".filter-btn"));
    const emptyState = document.getElementById("no-tool-results");
    let activeCategory = "all";

    function filterCards() {
        const query = (search?.value || "").trim().toLowerCase();
        let visibleCount = 0;
        cards.forEach(card => {
            const categoryMatches = activeCategory === "all" || card.dataset.category === activeCategory;
            const searchMatches = !query || card.dataset.search.includes(query);
            const visible = categoryMatches && searchMatches;
            card.hidden = !visible;
            visibleCount += visible ? 1 : 0;
        });
        if (emptyState) emptyState.hidden = visibleCount !== 0;
    }

    search?.addEventListener("input", filterCards);
    filters.forEach(button => {
        button.addEventListener("click", () => {
            filters.forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            activeCategory = button.dataset.filter || "all";
            filterCards();
        });
    });
});
