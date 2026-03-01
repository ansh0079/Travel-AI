'use client';

import { useState, useEffect } from 'react';
import { api, RedditPost, RedditInsightsResponse } from '@/services/api';

interface RedditInsightsProps {
  cityName: string;
}

function timeAgo(utc: number): string {
  const seconds = Math.floor(Date.now() / 1000 - utc);
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 2592000) return `${Math.floor(seconds / 86400)}d ago`;
  return `${Math.floor(seconds / 2592000)}mo ago`;
}

function formatScore(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

function PostCard({ post }: { post: RedditPost }) {
  return (
    <a
      href={post.permalink}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col gap-2 bg-white border border-gray-100 rounded-xl p-4 shadow-sm hover:shadow-md hover:border-orange-200 transition-all"
    >
      {/* Subreddit + flair */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-semibold text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full">
          r/{post.subreddit}
        </span>
        {post.flair && (
          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
            {post.flair}
          </span>
        )}
        <span className="ml-auto text-xs text-gray-400">{timeAgo(post.created_utc)}</span>
      </div>

      {/* Title */}
      <p className="text-sm font-medium text-gray-900 leading-snug group-hover:text-orange-700 transition-colors line-clamp-3">
        {post.title}
      </p>

      {/* Preview text */}
      {post.preview_text && (
        <p className="text-xs text-gray-500 line-clamp-2">{post.preview_text}</p>
      )}

      {/* Score + Comments */}
      <div className="flex items-center gap-4 mt-auto pt-1 border-t border-gray-50">
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <svg className="w-3.5 h-3.5 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 3l2.39 4.84 5.34.78-3.87 3.77.91 5.32L10 15.27l-4.77 2.51.91-5.32L2.27 8.62l5.34-.78z" />
          </svg>
          {formatScore(post.score)}
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          {post.num_comments.toLocaleString()} comments
        </span>
        <span className="ml-auto text-xs text-orange-500 opacity-0 group-hover:opacity-100 transition-opacity">
          View on Reddit →
        </span>
      </div>
    </a>
  );
}

export default function RedditInsights({ cityName }: RedditInsightsProps) {
  const [data, setData] = useState<RedditInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!cityName) return;
    setLoading(true);
    api
      .getRedditInsights(cityName)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [cityName]);

  if (loading) {
    return (
      <div className="mt-8">
        <div className="flex items-center gap-2 mb-4">
          <RedditLogo />
          <h3 className="font-bold text-gray-800">Community Insights</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-36 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.posts.length === 0) return null;

  return (
    <div className="mt-8">
      <div className="flex items-center gap-2 mb-1 flex-wrap">
        <RedditLogo />
        <h3 className="font-bold text-gray-800">Reddit Community Insights</h3>
        {data.community_subreddit && (
          <a
            href={`https://reddit.com/${data.community_subreddit}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-orange-600 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded-full hover:bg-orange-100 transition-colors"
          >
            {data.community_subreddit} ↗
          </a>
        )}
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full ml-auto">
          {data.posts.length} posts
        </span>
      </div>
      <p className="text-xs text-gray-400 mb-4">
        Top posts from r/travel, r/solotravel, r/backpacking and more
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>
    </div>
  );
}

function RedditLogo() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="10" r="10" fill="#FF4500" />
      <path
        d="M16.67 10a1.46 1.46 0 00-2.47-1 7.12 7.12 0 00-3.85-1.23l.65-3.06 2.13.45a1 1 0 101.05-1 1 1 0 00-.95.68l-2.38-.5a.17.17 0 00-.2.13l-.73 3.41a7.14 7.14 0 00-3.82 1.23 1.46 1.46 0 10-1.61 2.39 2.87 2.87 0 000 .44c0 2.24 2.61 4.06 5.83 4.06s5.83-1.82 5.83-4.06a2.87 2.87 0 000-.44 1.46 1.46 0 00.42-1zm-9.4 1.17a1 1 0 111 1 1 1 0 01-1-1zm5.57 2.64a3.5 3.5 0 01-2.84.77 3.5 3.5 0 01-2.84-.77.17.17 0 01.24-.24 3.18 3.18 0 002.6.64 3.18 3.18 0 002.6-.64.17.17 0 11.24.24zm-.17-1.64a1 1 0 111-1 1 1 0 01-1 1z"
        fill="white"
      />
    </svg>
  );
}
