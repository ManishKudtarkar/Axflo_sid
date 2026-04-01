/* ============================================================
   AXFLO - Main JavaScript File (Final)
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  initThemeToggle();
  initMobileMenu();
  initHeaderScroll();
  initBuyModal();
  initProductFiltering();
  initRevealOnScroll();
});

/**
 * --- 1. Theme (Dark/Light) ---
 * Manages the dark/light mode toggle using a common class.
 * Saves preference in localStorage.
 */
function initThemeToggle() {
  const THEME_KEY = "axflow_theme";
  // Use class selector for all theme buttons
  const themeToggles = document.querySelectorAll(".theme-toggle-btn");

  if (themeToggles.length === 0) return; // No buttons found

  function setTheme(theme) {
    document.body.classList.toggle("dark-mode", theme === "dark");
    localStorage.setItem(THEME_KEY, theme);
    updateButtonIcons(theme === "dark");
  }

  function updateButtonIcons(isDark) {
    themeToggles.forEach(btn => {
      btn.textContent = isDark ? "☀️" : "🌙";
    });
  }

  themeToggles.forEach(btn => {
    btn.addEventListener("click", () => {
      const isDark = document.body.classList.toggle("dark-mode");
      localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
      updateButtonIcons(isDark);
    });
  });

  // Set initial theme on page load
  const savedTheme = localStorage.getItem(THEME_KEY) || "light";
  setTheme(savedTheme);
}

/**
 * --- 2. Mobile (Hamburger) Menu ---
 * Toggles the visibility of the mobile navigation menu
 * and animates the hamburger icon.
 */
function initMobileMenu() {
  const nav = document.querySelector(".nav");
  const navToggle = document.querySelector(".nav-toggle");

  if (!nav || !navToggle) return;

  navToggle.addEventListener("click", () => {
    const isVisible = nav.classList.toggle("nav-visible");
    
    // Toggle the 'active' class on the hamburger button
    navToggle.classList.toggle("active"); 
    
    // Update ARIA attribute for accessibility
    navToggle.setAttribute("aria-expanded", isVisible); 
    
    // ADD THIS LINE: Toggles scroll-lock on the body
    document.body.classList.toggle("noscroll", isVisible);
  });
}

/**
 * --- 3. Header Scroll Effect ---
 * Changes header from transparent to solid on scroll (homepage).
 */
function initHeaderScroll() {
  const header = document.querySelector(".site-header-transparent");
  if (!header) return;

  let isScrolled = false;
  const scrollThreshold = 50; // Pixels to scroll before changing header

  const handleScroll = () => {
    if (window.scrollY > scrollThreshold && !isScrolled) {
      header.classList.add("header-scrolled");
      isScrolled = true;
    } else if (window.scrollY <= scrollThreshold && isScrolled) {
      header.classList.remove("header-scrolled");
      isScrolled = false;
    }
  };

  // Run on initial load in case page is already scrolled
  handleScroll();

  // Attach listener
  window.addEventListener("scroll", handleScroll, { passive: true }); // Use passive for performance
}


/**
 * --- 4. "Buy Now" Modal ---
 * Handles opening the modal and submitting the order form via API.
 * Note: Modal is primarily on index.html, if used.
 */
function initBuyModal() {
  const modal = document.getElementById("buy-modal");
  if (!modal) return; // No modal on this page

  // Select elements within the modal once
  const buyBtns = document.querySelectorAll(".buy-btn"); // Buttons that trigger the modal
  const modalClose = modal.querySelector(".modal-close");
  const modalCancel = modal.querySelector("#modal-cancel");
  const modalImg = modal.querySelector("#modal-img");
  const modalTitle = modal.querySelector("#modal-title");
  const modalDesc = modal.querySelector("#modal-desc");
  const modalPrice = modal.querySelector("#modal-price");
  const buyForm = modal.querySelector("#buy-form");
  const firstInput = buyForm?.querySelector("input[name='buyer']"); // Optional chaining

  function openModalFromCard(card) {
    const name = card.getAttribute("data-name") || "Product";
    const price = card.getAttribute("data-price") || "";
    const desc = card.getAttribute("data-desc") || "";
    const img = card.getAttribute("data-img") || "";

    // Safely update elements only if they exist
    if (modalImg) { modalImg.src = img; modalImg.alt = name; }
    if (modalTitle) modalTitle.textContent = name;
    if (modalDesc) modalDesc.textContent = desc;
    if (modalPrice) modalPrice.innerHTML = price; // Use innerHTML for HTML entities like &#8377;

    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");

    // Focus first input for accessibility
    firstInput?.focus();
  }

  function closeModal() {
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  // Attach listeners to all "Buy Now" buttons
  buyBtns.forEach(btn => {
    btn.addEventListener("click", (ev) => {
      const card = ev.currentTarget.closest(".product-card");
      if (card) openModalFromCard(card);
    });
  });

  // Form submission logic
  if (buyForm) {
    buyForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const buyer = buyForm.buyer?.value;
      const contact = buyForm.contact?.value;
      const productName = modalTitle?.textContent || "Unknown Product";

      const orderData = { productName, buyer, contact };

      // Send data to the Flask API using fetch
      fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(orderData),
      })
      .then(response => {
        if (!response.ok) {
          // Throw an error if response status is not 2xx
          throw new Error(`Network response was not ok: ${response.statusText}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.success) {
          alert(`Thank you, ${buyer}! Your order inquiry for ${productName} has been received.`);
        } else {
          // Use server message if available, otherwise generic
          alert(data.message || 'Something went wrong. Please try again.');
        }
        closeModal();
        buyForm.reset();
      })
      .catch(error => {
        console.error('Fetch Error:', error);
        // Provide a more user-friendly error message
        alert('Failed to submit order. Please check your internet connection or try again later.');
      });
    });
  }

  // Close modal listeners
  modalClose?.addEventListener("click", closeModal);
  modalCancel?.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); }); // Backdrop click
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && modal.classList.contains("show")) closeModal(); });
}

/**
 * --- 5. Product Filtering ---
 * Filters products on the /products page based on category.
 * Includes a "no results" message.
 */
function initProductFiltering() {
  const filterContainer = document.querySelector(".filter-container");
  const productGrid = document.getElementById("product-grid");
  const noResultsMessage = document.getElementById("no-results-message");

  // If essential elements don't exist, exit
  if (!filterContainer || !productGrid) return;

  const filterButtons = filterContainer.querySelectorAll(".filter-btn");
  const productCards = productGrid.querySelectorAll(".product-card");

  if (filterButtons.length === 0 || productCards.length === 0) return; // Nothing to filter

  filterButtons.forEach(button => {
    button.addEventListener("click", () => {
      const filterValue = button.getAttribute("data-filter");

      // Update active button style
      filterButtons.forEach(btn => btn.classList.remove("active"));
      button.classList.add("active");

      let visibleCount = 0;
      // Show/Hide products based on category
      productCards.forEach(card => {
        const cardCategory = card.getAttribute("data-category");
        const shouldShow = (filterValue === "all" || cardCategory === filterValue);

        // Toggle visibility
        card.style.display = shouldShow ? "flex" : "none";

        if (shouldShow) visibleCount++;
      });

      // Show or hide the "no results" message
      if (noResultsMessage) {
        noResultsMessage.style.display = (visibleCount === 0) ? 'block' : 'none';
      }
    });
  });
}


/**
 * --- 6. Reveal on Scroll Animation ---
 * Uses IntersectionObserver for fade-in effect.
 */
function initRevealOnScroll() {
  const elementsToAnimate = document.querySelectorAll(
    ".hero-copy, .hero-media, .product-card, .key-feature-card, " +
    ".testimonial-card, .cta-banner, .about-section, .contact-section, " +
    ".event-card, .product-detail-layout, .page-head, .section-head, .hero-gallery, .client-logos"
  );

  // Check if IntersectionObserver is supported
  if (!("IntersectionObserver" in window)) {
    elementsToAnimate.forEach(el => { if (el) el.style.opacity = 1; });
    console.warn("IntersectionObserver not supported, reveal animations disabled.");
    return;
  }

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = 1;
        entry.target.style.transform = "translateY(0)";
        obs.unobserve(entry.target); // Unobserve after animating
      }
    });
  }, {
       threshold: 0.1, // Start when 10% visible
       rootMargin: "0px 0px -50px 0px" // Start a bit early
      });

  elementsToAnimate.forEach(el => {
    if (el) {
      el.style.opacity = 0;
      el.style.transform = "translateY(20px)";
      el.style.transition = "opacity 0.6s ease-out, transform 0.6s ease-out";
      el.style.willChange = "opacity, transform"; // Performance hint
      observer.observe(el);
    }
  });
}
