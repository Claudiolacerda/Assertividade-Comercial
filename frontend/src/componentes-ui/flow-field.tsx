/**
 * @name: FlowField
 * @description: Canvas particle flow field background — organic noise-driven streams of glowing light.
 * @version: 1.0.0
 * @author: @dorian_baffier
 * @license: MIT
 * @website: https://kokonutui.com
 * @github: https://github.com/kokonut-labs/kokonutui
 *
 * ---------------------------------------------------------------------------
 * Adaptado para o Neriah. O algoritmo do campo e o laço de partículas são os
 * originais. Mudou o que precisava mudar para ele servir de FUNDO de uma seção
 * (e não de página inteira), e três coisas que estavam erradas para este uso:
 *
 * 1. Tema `neriah`: o verde da marca, com deriva de matiz estreita. Os temas
 *    originais varrem até 200° de matiz e devolveriam um arco-íris, o que
 *    brigaria com a regra de um acento só deste sistema.
 * 2. O `ctx.scale(dpr, dpr)` era cumulativo: cada `resize` multiplicava a
 *    escala anterior, então duas mudanças de tamanho já desenhavam em 4x.
 *    Agora a matriz é reiniciada antes.
 * 3. Media o `window`, não o elemento. Como fundo de seção isso pintava uma
 *    tela inteira atrás de um bloco de 900px.
 * 4. Não parava nunca. Agora respeita `prefers-reduced-motion`, para quando sai
 *    da tela e para quando a aba fica oculta — um laço de 1200 partículas
 *    rodando atrás de conteúdo que ninguém está vendo é gasto de bateria.
 *
 * O `DefaultContent` original foi removido junto com a dependência `motion`:
 * aqui o conteúdo do Hero sempre vem por `children`, então era código morto que
 * ainda assim traria uma biblioteca de animação para o pacote.
 * ---------------------------------------------------------------------------
 */

import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type ColorTheme = "aurora" | "ember" | "ocean" | "neriah";
type ParticleDensity = "sparse" | "medium" | "dense";

interface Particle {
  x: number;
  y: number;
  speed: number;
  hue: number;
  life: number;
  maxLife: number;
}

interface ThemeConfig {
  hueStart: number;
  hueRange: number;
  /** quanto a direção do campo desloca o matiz; alto vira arco-íris */
  hueDrift: number;
  saturation: number;
  lightness: number;
  bg: string;
  trailAlpha: number;
}

export interface FlowFieldProps {
  className?: string;
  children?: ReactNode;
  theme?: ColorTheme;
  density?: ParticleDensity;
  /** raio do ponto; abaixo de 1 o campo vira poeira em vez de fluxo */
  dotSize?: number;
  /** opacidade do conjunto, para o efeito poder ser cenário e não protagonista */
  intensity?: number;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PARTICLE_COUNTS: Record<ParticleDensity, number> = {
  sparse: 600,
  medium: 1200,
  dense: 2000,
} as const;

const THEMES: Record<ColorTheme, ThemeConfig> = {
  aurora: { hueStart: 120, hueRange: 200, hueDrift: 70, saturation: 90, lightness: 62, bg: "5, 5, 8", trailAlpha: 0.06 },
  ember: { hueStart: 0, hueRange: 55, hueDrift: 70, saturation: 95, lightness: 58, bg: "8, 4, 2", trailAlpha: 0.07 },
  ocean: { hueStart: 180, hueRange: 90, hueDrift: 70, saturation: 88, lightness: 60, bg: "2, 6, 10", trailAlpha: 0.06 },
  /* O verde da logo é hsl(140, 83%, 63%). A faixa e a deriva são estreitas de
     propósito: o campo varia entre tons de verde, nunca sai da marca.
     A luminosidade é baixa por obrigação, não por gosto: o canal verde pesa
     0,71 na luminância, então um verde claro atrás de texto de corpo estoura o
     contraste. Em 34% ele continua nitidamente verde contra o preto da marca e
     cabe no teto de 0,0587 de luminância que o parágrafo do Hero exige. */
  neriah: { hueStart: 126, hueRange: 30, hueDrift: 18, saturation: 88, lightness: 34, bg: "4, 13, 12", trailAlpha: 0.045 },
} as const;

// ─── Noise / vector-field ─────────────────────────────────────────────────────

/**
 * Smooth organic 2D noise via a multi-octave trigonometric series.
 * Returns an angle in radians that evolves continuously with time `t`.
 */
function fieldAngle(x: number, y: number, t: number): number {
  const s = 0.0025;
  return (
    Math.sin(x * s + t * 0.0007) * Math.PI +
    Math.cos(y * s + t * 0.0005) * Math.PI +
    Math.sin((x + y) * s * 0.6 + t * 0.0009) * Math.PI * 0.6 +
    Math.cos((x - y) * s * 0.4 + t * 0.0006) * Math.PI * 0.4
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function FlowField({
  className,
  children,
  theme = "aurora",
  density = "medium",
  dotSize = 1.3,
  intensity = 1,
}: FlowFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const caixaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const caixa = caixaRef.current;
    if (!canvas || !caixa) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cfg = THEMES[theme];
    const count = PARTICLE_COUNTS[density];
    const dpr = window.devicePixelRatio ?? 1;

    let width = 0;
    let height = 0;
    let animId = 0;
    let time = 0;
    let particles: Particle[] = [];
    let visivel = true;
    let rodando = false;

    const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const spawnParticle = (): Particle => {
      const maxLife = 200 + Math.floor(Math.random() * 300);
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        speed: 1.1 + Math.random() * 1.8,
        hue: cfg.hueStart + Math.random() * cfg.hueRange,
        life: Math.floor(Math.random() * maxLife),
        maxLife,
      };
    };

    const resize = () => {
      // O elemento, não a janela: como fundo de seção, medir o `window` pintaria
      // uma tela inteira atrás de um bloco que pode ter 900px.
      const r = caixa.getBoundingClientRect();
      width = Math.max(1, Math.round(r.width));
      height = Math.max(1, Math.round(r.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      // setTransform antes de scale: sem isto cada resize multiplica a escala
      // anterior e o desenho sai cada vez maior.
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);

      ctx.fillStyle = `rgb(${cfg.bg})`;
      ctx.fillRect(0, 0, width, height);

      particles = Array.from({ length: count }, spawnParticle);
    };

    const passo = () => {
      time++;

      ctx.fillStyle = `rgba(${cfg.bg}, ${cfg.trailAlpha})`;
      ctx.fillRect(0, 0, width, height);

      for (const p of particles) {
        const angle = fieldAngle(p.x, p.y, time);

        p.x += Math.cos(angle) * p.speed;
        p.y += Math.sin(angle) * p.speed;
        p.life++;

        if (p.life > p.maxLife) {
          p.x = Math.random() * width;
          p.y = Math.random() * height;
          p.life = 0;
          p.hue = cfg.hueStart + Math.random() * cfg.hueRange;
          continue;
        }

        if (p.x < 0) p.x += width;
        else if (p.x > width) p.x -= width;
        if (p.y < 0) p.y += height;
        else if (p.y > height) p.y -= height;

        const progress = p.life / p.maxLife;
        const fadeIn = Math.min(progress * 8, 1);
        const fadeOut = Math.min((1 - progress) * 6, 1);
        const alpha = fadeIn * fadeOut * 0.9 * intensity;

        const hueMod = (p.hue + (angle / (Math.PI * 2)) * cfg.hueDrift + 360) % 360;

        ctx.beginPath();
        ctx.arc(p.x, p.y, dotSize, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hueMod}, ${cfg.saturation}%, ${cfg.lightness}%, ${alpha})`;
        ctx.fill();
      }
    };

    const render = () => {
      passo();
      animId = requestAnimationFrame(render);
    };

    const tocar = () => {
      if (rodando || semMovimento || !visivel || document.hidden) return;
      rodando = true;
      render();
    };
    const parar = () => {
      rodando = false;
      cancelAnimationFrame(animId);
    };

    resize();

    if (semMovimento) {
      // Quadro estático: o campo existe como textura, sem movimento nenhum.
      for (let i = 0; i < 90; i++) passo();
    } else {
      tocar();
    }

    const ro = new ResizeObserver(() => {
      resize();
      if (semMovimento) for (let i = 0; i < 90; i++) passo();
    });
    ro.observe(caixa);

    // Fora da tela não se desenha: 1200 partículas atrás de conteúdo que
    // ninguém está vendo é gasto de bateria.
    const io = new IntersectionObserver(
      ([e]) => {
        visivel = e.isIntersecting;
        visivel ? tocar() : parar();
      },
      { threshold: 0 },
    );
    io.observe(caixa);

    const aoTrocarAba = () => (document.hidden ? parar() : tocar());
    document.addEventListener("visibilitychange", aoTrocarAba);

    return () => {
      parar();
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", aoTrocarAba);
    };
  }, [theme, density, dotSize, intensity]);

  const bgColor = THEMES[theme].bg;

  return (
    <div
      ref={caixaRef}
      className={cn(
        "relative flex min-h-screen w-full items-center justify-center overflow-hidden",
        className,
      )}
      style={{ background: `rgb(${bgColor})` }}
    >
      <canvas aria-hidden="true" className="pointer-events-none absolute inset-0" ref={canvasRef} />

      {/* Radial vignette — focuses center, dims edges */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background: `radial-gradient(ellipse 65% 60% at 50% 50%, transparent 20%, rgba(${bgColor}, 0.92) 100%)`,
        }}
      />

      {/* Soft top / bottom fades */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-40"
        style={{ background: `linear-gradient(to bottom, rgb(${bgColor}), transparent)` }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-40"
        style={{ background: `linear-gradient(to top, rgb(${bgColor}), transparent)` }}
      />

      {children}
    </div>
  );
}
