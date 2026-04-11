import * as React from "react";
import * as ToastPrimitives from "@radix-ui/react-toast";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";

import { cn } from "../../lib/utils";

const ToastProvider = ToastPrimitives.Provider;

const ToastViewport = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Viewport>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Viewport>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Viewport
    ref={ref}
    className={cn(
      "fixed top-20 right-0 z-100 flex max-h-screen w-full flex-col p-4 md:max-w-[420px]",
      className,
    )}
    {...props}
  />
));
ToastViewport.displayName = ToastPrimitives.Viewport.displayName;

const toastVariants = cva(
  "group pointer-events-auto relative flex w-full items-start justify-between gap-4 overflow-hidden rounded-2xl border p-5 pr-9 shadow-[0_16px_48px_rgba(0,0,0,0.45)] backdrop-blur-xl transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-top-full",
  {
    variants: {
      variant: {
        default:
          "border-cyan-300/20 bg-[linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] text-[#ECECEC] ring-1 ring-white/10 before:pointer-events-none before:absolute before:inset-0 before:opacity-90 before:bg-[radial-gradient(600px_circle_at_20%_30%,rgba(3,234,236,0.22),transparent_55%),radial-gradient(600px_circle_at_80%_70%,rgba(143,87,255,0.16),transparent_60%)] before:content-[''] after:pointer-events-none after:absolute after:inset-0 after:opacity-[0.08] after:bg-[linear-gradient(to_right,rgba(255,255,255,0.8)_1px,transparent_1px)] after:bg-[size:48px_48px] after:content-['']",
        destructive:
          "destructive group border-rose-500/40 bg-[linear-gradient(135deg,rgba(239,68,68,0.95),rgba(220,38,38,0.92))] text-white ring-1 ring-rose-500/30 before:pointer-events-none before:absolute before:inset-0 before:opacity-90 before:bg-[radial-gradient(600px_circle_at_25%_35%,rgba(239,68,68,0.3),transparent_55%),radial-gradient(520px_circle_at_80%_70%,rgba(220,38,38,0.2),transparent_60%)] before:content-[''] after:pointer-events-none after:absolute after:inset-0 after:opacity-[0.15] after:bg-[linear-gradient(to_right,rgba(255,255,255,0.3)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.3)_1px,transparent_1px)] after:bg-[size:20px_20px] after:content-['']",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

const Toast = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Root> &
    VariantProps<typeof toastVariants>
>(({ className, variant, ...props }, ref) => {
  return (
    <ToastPrimitives.Root
      ref={ref}
      className={cn(toastVariants({ variant }), className)}
      {...props}
    />
  );
});
Toast.displayName = ToastPrimitives.Root.displayName;

const ToastAction = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Action>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Action>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Action
    ref={ref}
    className={cn(
      "relative inline-flex h-8 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/6 px-3 text-sm font-medium text-[#ECECEC] backdrop-blur-md transition-all hover:bg-white/10 hover:border-white/25 focus:outline-none focus:ring-2 focus:ring-[#03EAEC]/70 focus:ring-offset-2 focus:ring-offset-transparent group-[.destructive]:border-rose-200/20 group-[.destructive]:text-rose-50 group-[.destructive]:hover:border-rose-200/30 group-[.destructive]:focus:ring-rose-300/60 disabled:pointer-events-none disabled:opacity-50",
      className,
    )}
    {...props}
  />
));
ToastAction.displayName = ToastPrimitives.Action.displayName;

const ToastClose = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Close>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Close>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Close
    ref={ref}
    className={cn(
      "absolute right-2 top-2 rounded-lg p-1.5 text-[#A0AEC0] opacity-0 transition-all group-hover:opacity-100 hover:text-[#03EAEC] hover:bg-white/6 focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-[#03EAEC]/70 focus:ring-offset-2 focus:ring-offset-transparent group-[.destructive]:text-rose-200 group-[.destructive]:hover:text-rose-50 group-[.destructive]:focus:ring-rose-300/60",
      className,
    )}
    toast-close=""
    {...props}
  >
    <X className="h-4 w-4" />
  </ToastPrimitives.Close>
));
ToastClose.displayName = ToastPrimitives.Close.displayName;

const ToastTitle = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Title>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Title>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Title
    ref={ref}
    className={cn(
      "relative text-sm font-semibold tracking-wide text-[#ECECEC] group-[.destructive]:text-white group-[.destructive]:font-bold group-[.destructive]:drop-shadow-[0_1px_2px_rgba(0,0,0,0.3)]",
      className,
    )}
    {...props}
  />
));
ToastTitle.displayName = ToastPrimitives.Title.displayName;

const ToastDescription = React.forwardRef<
  React.ElementRef<typeof ToastPrimitives.Description>,
  React.ComponentPropsWithoutRef<typeof ToastPrimitives.Description>
>(({ className, ...props }, ref) => (
  <ToastPrimitives.Description
    ref={ref}
    className={cn(
      "relative text-sm text-[#A0AEC0] leading-relaxed group-[.destructive]:text-white group-[.destructive]:font-medium group-[.destructive]:drop-shadow-[0_1px_2px_rgba(0,0,0,0.3)]",
      className,
    )}
    {...props}
  />
));
ToastDescription.displayName = ToastPrimitives.Description.displayName;

type ToastProps = React.ComponentPropsWithoutRef<typeof Toast>;

type ToastActionElement = React.ReactElement<typeof ToastAction>;

export {
  type ToastProps,
  type ToastActionElement,
  ToastProvider,
  ToastViewport,
  Toast,
  ToastTitle,
  ToastDescription,
  ToastClose,
  ToastAction,
};
