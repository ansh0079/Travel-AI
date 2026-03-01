'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Star, MapPin, Clock, Phone, Globe, Camera, MessageSquare, ExternalLink } from 'lucide-react';
import { api } from '@/services/api';

interface AttractionDetailModalProps {
  attraction: {
    name: string;
    description: string;
    category: string;
    rating: number;
    price_level: string;
    location?: { lat: number; lon: number };
  } | null;
  cityName: string;
  isOpen: boolean;
  onClose: () => void;
}

interface AttractionDetails {
  name: string;
  description: string;
  rating: number;
  num_reviews: number;
  address: string;
  phone?: string;
  website?: string;
  hours?: string;
  photos: string[];
  reviews: Array<{
    id: string;
    title: string;
    text: string;
    rating: number;
    author: string;
    date: string;
  }>;
  ranking?: string;
  price_level?: string;
}

export default function AttractionDetailModal({ attraction, cityName, isOpen, onClose }: AttractionDetailModalProps) {
  const [details, setDetails] = useState<AttractionDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'photos' | 'reviews'>('overview');
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && attraction) {
      fetchAttractionDetails();
    }
  }, [isOpen, attraction]);

  const fetchAttractionDetails = async () => {
    if (!attraction) return;
    
    setLoading(true);
    try {
      // Try to get TripAdvisor data for this attraction
      const searchQuery = `${attraction.name} ${cityName}`;
      const tripAdvisorData = await api.getTripAdvisorAttractions(searchQuery, 1);
      
      if (tripAdvisorData.enabled && tripAdvisorData.attractions.length > 0) {
        const taAttraction = tripAdvisorData.attractions[0];
        
        // Get reviews if we have a location_id
        let reviews: AttractionDetails['reviews'] = [];
        if (taAttraction.location_id) {
          try {
            const reviewsData = await api.getTripAdvisorReviews(taAttraction.location_id);
            if (reviewsData.enabled) {
              reviews = reviewsData.reviews.map(r => ({
                id: r.id?.toString() || Math.random().toString(),
                title: r.title || '',
                text: r.text || '',
                rating: r.rating || 0,
                author: r.user?.username || 'Anonymous',
                date: r.published_date || '',
              }));
            }
          } catch (e) {
            console.log('Could not fetch reviews');
          }
        }

        setDetails({
          name: taAttraction.name || attraction.name,
          description: taAttraction.description || attraction.description,
          rating: taAttraction.rating || attraction.rating,
          num_reviews: taAttraction.num_reviews || 0,
          address: taAttraction.address || '',
          photos: taAttraction.photo_url ? [taAttraction.photo_url] : [],
          reviews,
          ranking: taAttraction.ranking_string,
          price_level: taAttraction.price_level || attraction.price_level,
          website: taAttraction.web_url,
        });
      } else {
        // Fallback to basic data
        setDetails({
          name: attraction.name,
          description: attraction.description,
          rating: attraction.rating,
          num_reviews: 0,
          address: '',
          photos: [],
          reviews: [],
          price_level: attraction.price_level,
        });
      }
    } catch (error) {
      console.error('Error fetching attraction details:', error);
      setDetails({
        name: attraction?.name || '',
        description: attraction?.description || '',
        rating: attraction?.rating || 0,
        num_reviews: 0,
        address: '',
        photos: [],
        reviews: [],
        price_level: attraction?.price_level || '',
      });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !attraction) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden"
        >
          {/* Header */}
          <div className="relative h-48 bg-gradient-to-br from-blue-600 to-purple-700">
            {details?.photos[0] ? (
              <img
                src={details.photos[0]}
                alt={details.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Camera className="w-16 h-16 text-white/30" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 bg-black/30 hover:bg-black/50 rounded-full text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="absolute bottom-4 left-6 right-6">
              <h2 className="text-2xl font-bold text-white mb-1">{details?.name || attraction.name}</h2>
              <div className="flex items-center gap-3 text-white/90">
                <span className="flex items-center gap-1">
                  <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  {details?.rating || attraction.rating}
                </span>
                {details?.num_reviews > 0 && (
                  <span className="text-sm">({details.num_reviews.toLocaleString()} reviews)</span>
                )}
                <span className="bg-white/20 px-2 py-0.5 rounded-full text-sm">
                  {attraction.category}
                </span>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200">
            {[
              { id: 'overview', label: 'Overview', icon: MapPin },
              { id: 'photos', label: `Photos (${details?.photos.length || 0})`, icon: Camera },
              { id: 'reviews', label: `Reviews (${details?.reviews.length || 0})`, icon: MessageSquare },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="p-6 max-h-[50vh] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              </div>
            ) : (
              <>
                {/* Overview Tab */}
                {activeTab === 'overview' && (
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold text-gray-900 mb-2">About</h3>
                      <p className="text-gray-600 leading-relaxed">{details?.description || attraction.description}</p>
                    </div>

                    {details?.ranking && (
                      <div className="bg-green-50 text-green-800 px-4 py-2 rounded-lg inline-block">
                        {details.ranking}
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      {details?.address && (
                        <div className="flex items-start gap-2">
                          <MapPin className="w-5 h-5 text-gray-400 mt-0.5" />
                          <div>
                            <p className="font-medium text-sm">Address</p>
                            <p className="text-gray-600 text-sm">{details.address}</p>
                          </div>
                        </div>
                      )}

                      {details?.price_level && (
                        <div className="flex items-start gap-2">
                          <div className="w-5 h-5 flex items-center justify-center text-gray-400 font-bold">$</div>
                          <div>
                            <p className="font-medium text-sm">Price Range</p>
                            <p className="text-gray-600 text-sm">{details.price_level}</p>
                          </div>
                        </div>
                      )}

                      {details?.hours && (
                        <div className="flex items-start gap-2">
                          <Clock className="w-5 h-5 text-gray-400 mt-0.5" />
                          <div>
                            <p className="font-medium text-sm">Hours</p>
                            <p className="text-gray-600 text-sm">{details.hours}</p>
                          </div>
                        </div>
                      )}

                      {details?.phone && (
                        <div className="flex items-start gap-2">
                          <Phone className="w-5 h-5 text-gray-400 mt-0.5" />
                          <div>
                            <p className="font-medium text-sm">Phone</p>
                            <p className="text-gray-600 text-sm">{details.phone}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {details?.website && (
                      <a
                        href={details.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 transition-colors"
                      >
                        <Globe className="w-4 h-4" />
                        View on TripAdvisor
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                )}

                {/* Photos Tab */}
                {activeTab === 'photos' && (
                  <div>
                    {details?.photos && details.photos.length > 0 ? (
                      <div className="grid grid-cols-2 gap-3">
                        {details.photos.map((photo, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedPhoto(photo)}
                            className="relative aspect-square rounded-lg overflow-hidden hover:opacity-90 transition-opacity"
                          >
                            <img
                              src={photo}
                              alt={`${details.name} photo ${idx + 1}`}
                              className="w-full h-full object-cover"
                            />
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-12 text-gray-500">
                        <Camera className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p>No photos available</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Reviews Tab */}
                {activeTab === 'reviews' && (
                  <div className="space-y-4">
                    {details?.reviews && details.reviews.length > 0 ? (
                      details.reviews.map((review) => (
                        <div key={review.id} className="border-b border-gray-100 pb-4 last:border-0">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="flex items-center gap-1">
                              {[...Array(5)].map((_, i) => (
                                <Star
                                  key={i}
                                  className={`w-4 h-4 ${
                                    i < review.rating
                                      ? 'fill-yellow-400 text-yellow-400'
                                      : 'text-gray-200'
                                  }`}
                                />
                              ))}
                            </div>
                            <span className="text-sm text-gray-500">{review.author}</span>
                            {review.date && (
                              <span className="text-sm text-gray-400">• {new Date(review.date).toLocaleDateString()}</span>
                            )}
                          </div>
                          {review.title && (
                            <p className="font-medium text-gray-900 mb-1">{review.title}</p>
                          )}
                          <p className="text-gray-600 text-sm line-clamp-4">{review.text}</p>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-12 text-gray-500">
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p>No reviews available</p>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </motion.div>

        {/* Photo Lightbox */}
        {selectedPhoto && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-4"
            onClick={() => setSelectedPhoto(null)}
          >
            <button
              onClick={() => setSelectedPhoto(null)}
              className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full text-white"
            >
              <X className="w-6 h-6" />
            </button>
            <img
              src={selectedPhoto}
              alt="Enlarged view"
              className="max-w-full max-h-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </motion.div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
