import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Junta classes e resolve conflitos do Tailwind. Esperado pelos componentes
 *  do shadcn; aqui ele convive com as classes semânticas do Neriah. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
