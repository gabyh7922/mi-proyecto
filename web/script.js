// ===== Año en el footer =====
document.getElementById("year").textContent = new Date().getFullYear();

// ===== Nav: fondo al hacer scroll =====
const nav = document.getElementById("nav");
addEventListener("scroll", () => nav.classList.toggle("scrolled", scrollY > 30));

// ===== Menú móvil =====
const burger = document.getElementById("burger");
const navLinks = document.querySelector(".nav-links");
burger.addEventListener("click", () => navLinks.classList.toggle("open"));
navLinks.querySelectorAll("a").forEach(a =>
  a.addEventListener("click", () => navLinks.classList.remove("open"))
);

// ===== Reveal al hacer scroll =====
const io = new IntersectionObserver(
  entries => entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }),
  { threshold: 0.15 }
);
document.querySelectorAll(".reveal").forEach(el => io.observe(el));

// ===== Contador animado de estadísticas =====
const counters = document.querySelectorAll(".stat-num");
const counterIO = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (!e.isIntersecting) return;
    const el = e.target;
    const target = +el.dataset.count;
    let n = 0;
    const step = Math.max(1, Math.ceil(target / 40));
    const tick = () => {
      n = Math.min(target, n + step);
      el.textContent = n;
      if (n < target) requestAnimationFrame(tick);
    };
    tick();
    counterIO.unobserve(el);
  });
}, { threshold: 0.5 });
counters.forEach(c => counterIO.observe(c));

// ===== Tilt 3D en las tarjetas =====
document.querySelectorAll(".tilt").forEach(card => {
  card.addEventListener("mousemove", e => {
    const r = card.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    card.style.transform = `perspective(800px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-6px)`;
  });
  card.addEventListener("mouseleave", () => (card.style.transform = ""));
});

// ===== Formulario (demo: abre el cliente de correo) =====
const form = document.getElementById("contact-form");
form.addEventListener("submit", e => {
  e.preventDefault();
  const d = new FormData(form);
  const subject = encodeURIComponent(`Nuevo contacto web — ${d.get("nombre")}`);
  const body = encodeURIComponent(`Nombre: ${d.get("nombre")}\nCorreo: ${d.get("email")}\n\n${d.get("mensaje")}`);
  location.href = `mailto:contacto@neuralsynk.cl?subject=${subject}&body=${body}`;
});

// ===== Fondo animado: red neuronal de partículas =====
(() => {
  const canvas = document.getElementById("neural-bg");
  const ctx = canvas.getContext("2d");
  let w, h, particles, mouse = { x: -999, y: -999 };

  const COLORS = ["#00e5ff", "#a855f7", "#ff2bd6"];

  function resize() {
    w = canvas.width = innerWidth;
    h = canvas.height = innerHeight;
    const count = Math.min(110, Math.floor((w * h) / 16000));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      r: Math.random() * 1.8 + 0.6,
      c: COLORS[(Math.random() * COLORS.length) | 0],
    }));
  }

  addEventListener("resize", resize);
  addEventListener("mousemove", e => { mouse.x = e.clientX; mouse.y = e.clientY; });
  addEventListener("mouseleave", () => { mouse.x = mouse.y = -999; });

  function draw() {
    ctx.clearRect(0, 0, w, h);

    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;

      // atracción suave hacia el cursor
      const dx = mouse.x - p.x, dy = mouse.y - p.y;
      const dist = Math.hypot(dx, dy);
      if (dist < 140) { p.x += dx * 0.012; p.y += dy * 0.012; }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.c;
      ctx.fill();
    }

    // líneas entre partículas cercanas
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 130) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(120,160,255,${(1 - d / 130) * 0.18})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  resize();
  if (!matchMedia("(prefers-reduced-motion: reduce)").matches) draw();
})();
