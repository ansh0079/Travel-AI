'use client';

import { motion } from 'framer-motion';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div className={`skeleton rounded-lg ${className}`} />
  );
}

interface CardSkeletonProps {
  count?: number;
}

export function DestinationCardSkeleton({ count = 3 }: CardSkeletonProps) {
  return (
    <>
      {[...Array(count)].map((_, i) => (
        <div key={i} className="relative h-96 overflow-hidden rounded-3xl">
          <Skeleton className="absolute inset-0 h-full w-full" />
          <div className="absolute bottom-0 left-0 right-0 p-6 space-y-3">
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        </div>
      ))}
    </>
  );
}

export function ChatMessageSkeleton() {
  return (
    <div className="flex gap-3">
      <Skeleton className="w-10 h-10 rounded-2xl flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

export function FeatureCardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <>
      {[...Array(count)].map((_, i) => (
        <div key={i} className="p-6 rounded-3xl space-y-4">
          <Skeleton className="w-14 h-14 rounded-2xl" />
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      ))}
    </>
  );
}

export function StatsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="text-center space-y-2">
          <Skeleton className="h-12 w-24 mx-auto" />
          <Skeleton className="h-4 w-32 mx-auto" />
        </div>
      ))}
    </div>
  );
}

export function TestimonialSkeleton() {
  return (
    <div className="max-w-4xl mx-auto text-center space-y-6">
      <div className="flex justify-center gap-2">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="w-6 h-6 rounded-full" />
        ))}
      </div>
      <Skeleton className="h-6 w-full" />
      <Skeleton className="h-6 w-5/6 mx-auto" />
      <Skeleton className="h-6 w-4/6 mx-auto" />
      <div className="flex items-center justify-center gap-4">
        <Skeleton className="w-14 h-14 rounded-full" />
        <div className="text-left space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
    </div>
  );
}

export function HeroSkeleton() {
  return (
    <div className="min-h-screen flex items-center justify-center pt-20">
      <div className="container-modern text-center px-4 space-y-8">
        <Skeleton className="h-10 w-64 mx-auto rounded-full" />
        <div className="space-y-4">
          <Skeleton className="h-16 w-full max-w-2xl mx-auto" />
          <Skeleton className="h-16 w-3/4 max-w-2xl mx-auto" />
        </div>
        <div className="flex gap-4 justify-center">
          <Skeleton className="h-14 w-48 rounded-full" />
          <Skeleton className="h-14 w-48 rounded-full" />
        </div>
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-32 rounded-xl" />
      </div>
      <div className="grid md:grid-cols-3 gap-6">
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-32 rounded-2xl" />
      </div>
      <Skeleton className="h-96 rounded-3xl" />
    </div>
  );
}

export function ItinerarySkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex gap-4 p-4 rounded-2xl border border-white/10">
          <Skeleton className="w-16 h-16 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function FlightHotelSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="flex gap-4 p-4 rounded-2xl border border-white/10">
          <Skeleton className="w-24 h-24 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-1/2" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <div className="flex items-center justify-between mt-3">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-8 w-24 rounded-lg" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        className="w-12 h-12 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full"
      />
      <p className="text-gray-400">{message}</p>
    </div>
  );
}

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      {description && (
        <p className="text-gray-400 text-sm max-w-md mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="min-h-screen bg-[#0a0a19] flex items-center justify-center">
      <div className="text-center space-y-4">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-emerald-400 via-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-emerald-500/30"
        >
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          >
            ✈️
          </motion.span>
        </motion.div>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-gray-400"
        >
          Preparing your adventure...
        </motion.p>
      </div>
    </div>
  );
}
