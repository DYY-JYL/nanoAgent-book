document.addEventListener("DOMContentLoaded", () => {
  const articleHero = document.querySelector(".article-hero");
  const heroTitle = articleHero?.querySelector("h1");
  const body = document.body;

  if (articleHero && heroTitle && body.classList.contains("article-body")) {
    const updateReadingState = () => {
      const collapseAfter = Math.min(96, Math.max(40, articleHero.offsetHeight * 0.22));
      body.classList.toggle("is-reading", window.scrollY > collapseAfter);
    };

    updateReadingState();
    document.addEventListener("scroll", updateReadingState, { passive: true });
    window.addEventListener("resize", updateReadingState);
  }

  const progressBar = document.querySelector(".reading-progress-bar");
  if (progressBar) {
    const updateProgress = () => {
      const scrollTop = window.scrollY;
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      const ratio = scrollHeight > 0 ? Math.min(scrollTop / scrollHeight, 1) : 0;
      progressBar.style.width = `${ratio * 100}%`;
    };

    updateProgress();
    document.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
  }

  function parseCmdBlocks(text) {
    const paragraphs = text.split(/\n[ \t]*\n/).map((p) => p.trim()).filter(Boolean);

    if (paragraphs.length >= 2) {
      return paragraphs.map((p) => {
        const lines = p.split("\n");
        const label = lines
          .filter((l) => /^#/.test(l.trim()))
          .map((l) => l.replace(/^#\s*\d*\.?\s*/, "").trim())
          .join(" ");
        const command = lines.filter((l) => !/^#/.test(l.trim()) && l.trim()).join("\n");
        return { label, command };
      });
    }

    const cmdLines = text.split("\n").filter((l) => l.trim() && !/^#/.test(l.trim()));
    if (cmdLines.length <= 1) return [{ label: "", command: text }];
    return cmdLines.map((l) => ({ label: "", command: l }));
  }

  function makeCopyBtn(textToCopy) {
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.setAttribute("aria-label", "复制命令");
    btn.textContent = "复制";
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(textToCopy).then(() => {
        btn.textContent = "✓ 已复制";
        btn.classList.add("is-copied");
        setTimeout(() => {
          btn.textContent = "复制";
          btn.classList.remove("is-copied");
        }, 2000);
      });
    });
    return btn;
  }

  document.querySelectorAll(".demo-box").forEach((box) => {
    const pre = box.querySelector(".demo-command");
    const labelEl = box.querySelector(".lesson-index");
    if (!pre || !labelEl) return;

    const rawText = (pre.querySelector("code") || pre).textContent.trim();
    const blocks = parseCmdBlocks(rawText);

    if (blocks.length === 1) {
      labelEl.appendChild(makeCopyBtn(rawText));
    } else {
      const fragment = document.createDocumentFragment();
      blocks.forEach(({ label, command }) => {
        const subBlock = document.createElement("div");
        subBlock.className = "demo-sub-block";

        const head = document.createElement("div");
        head.className = "demo-sub-head";
        if (label) {
          const span = document.createElement("span");
          span.className = "demo-sub-label";
          span.textContent = label;
          head.appendChild(span);
        }
        head.appendChild(makeCopyBtn(command));
        subBlock.appendChild(head);

        const subPre = document.createElement("pre");
        subPre.className = "demo-command";
        const code = document.createElement("code");
        code.textContent = command;
        subPre.appendChild(code);
        subBlock.appendChild(subPre);

        fragment.appendChild(subBlock);
      });
      pre.replaceWith(fragment);
    }
  });

  const tocLinks = [...document.querySelectorAll(".toc-link[href^='#']")];
  if (!tocLinks.length) {
    return;
  }

  const sectionMap = tocLinks
    .map((link) => {
      const id = link.getAttribute("href").slice(1);
      const section = document.getElementById(id);
      return section ? { link, section } : null;
    })
    .filter(Boolean);

  if (!sectionMap.length) {
    return;
  }

  const activateLink = (activeId) => {
    for (const { link, section } of sectionMap) {
      link.classList.toggle("is-active", section.id === activeId);
    }
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visibleSections = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);

      if (visibleSections.length) {
        activateLink(visibleSections[0].target.id);
      }
    },
    {
      rootMargin: "-18% 0px -65% 0px",
      threshold: [0, 1],
    }
  );

  for (const { section } of sectionMap) {
    observer.observe(section);
  }

  activateLink(sectionMap[0].section.id);
});
