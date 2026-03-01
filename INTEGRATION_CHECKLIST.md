# ✅ Instagram & Influencer Integration Checklist

Use this checklist to track your integration progress.

---

## Backend Integration

### Database Models
- [ ] Add `Influencer` model to `backend/app/database/models.py`
- [ ] Add `SocialContent` model
- [ ] Add `UserInfluencerFollow` model
- [ ] Add `SavedSocialContent` model
- [ ] Add `Collection` model
- [ ] Add `UserInstagramConnection` model
- [ ] Create Alembic migration
- [ ] Run migration: `alembic upgrade head`

### Services Layer
- [ ] Create `backend/app/services/social_service.py`
- [ ] Create `backend/app/services/instagram_service.py`
- [ ] Implement influencer CRUD methods
- [ ] Implement feed generation logic
- [ ] Implement trending algorithm
- [ ] Implement follow/unfollow logic

### API Layer
- [ ] Create `backend/app/api/social_routes.py`
- [ ] Add feed endpoints (`GET /social/feed`)
- [ ] Add influencer endpoints (`GET /social/influencers`, `GET /social/influencers/{id}`)
- [ ] Add follow endpoints (`POST /social/influencers/{id}/follow`)
- [ ] Add trending endpoints (`GET /social/trending/destinations`)
- [ ] Add content endpoints (`POST /social/content/{id}/save`)
- [ ] Wire up router in `backend/app/main.py`

### Configuration
- [ ] Add Instagram API credentials to `.env`
- [ ] Configure CORS for Instagram OAuth redirects
- [ ] Set up rate limiting for external API calls

### Testing Data
- [ ] Create seed script
- [ ] Run seed script to populate test data
- [ ] Verify data in database

---

## Frontend Integration

### API Service
- [ ] Create `frontend/src/services/socialApi.ts`
- [ ] Define TypeScript interfaces
- [ ] Implement API functions
- [ ] Add React Query keys

### React Hooks
- [ ] Create `frontend/src/hooks/useSocial.ts`
- [ ] Implement `useSocialFeed` hook
- [ ] Implement `useInfluencers` hook
- [ ] Implement `useInfluencer` hook
- [ ] Implement `useFollowInfluencer` hook
- [ ] Implement `useTrendingDestinations` hook

### Components
- [ ] Copy `SocialFeed.tsx` component
- [ ] Copy `InfluencerHub.tsx` component
- [ ] Copy `TrendingDestinations.tsx` component
- [ ] Copy `TripInspiration.tsx` component
- [ ] Verify all imports are correct

### Pages
- [ ] Create `frontend/src/app/discover/page.tsx`
- [ ] Create `frontend/src/app/influencers/page.tsx`
- [ ] Create `frontend/src/app/trending/page.tsx`
- [ ] Create `frontend/src/app/inspiration/page.tsx`

### Navigation
- [ ] Add navigation links to header/sidebar
- [ ] Update mobile menu if applicable

### Styling
- [ ] Verify Tailwind classes work
- [ ] Check responsive design
- [ ] Test dark mode if applicable

---

## Third-Party Integration (Instagram)

### Meta Developer Setup
- [ ] Create Meta Developer account
- [ ] Create new app
- [ ] Add "Instagram Basic Display" product
- [ ] Configure OAuth settings
- [ ] Add redirect URIs

### App Configuration
- [ ] Get App ID and App Secret
- [ ] Add to backend `.env`
- [ ] Add to frontend environment

### OAuth Flow
- [ ] Create Instagram login button component
- [ ] Implement OAuth redirect handler
- [ ] Store access tokens securely
- [ ] Handle token refresh

### Permissions
- [ ] Request `instagram_basic` scope
- [ ] Request `instagram_content_publish` (optional)
- [ ] Submit for App Review
- [ ] Wait for approval (1-5 business days)

---

## Testing

### API Testing
- [ ] Test `/social/feed` endpoint
- [ ] Test `/social/influencers` endpoint
- [ ] Test `/social/influencers/{id}` endpoint
- [ ] Test follow/unfollow endpoints
- [ ] Test trending endpoints
- [ ] Test with authentication

### Frontend Testing
- [ ] Load social feed page
- [ ] Load influencers page
- [ ] Open influencer profile modal
- [ ] Test follow/unfollow buttons
- [ ] Test save content functionality
- [ ] Test infinite scroll
- [ ] Test responsive design

### Integration Testing
- [ ] Connect Instagram account
- [ ] Import Instagram posts
- [ ] Share content to Instagram
- [ ] Test error handling

### Performance Testing
- [ ] Check API response times
- [ ] Verify image loading
- [ ] Test with slow network
- [ ] Check memory usage

---

## Deployment

### Pre-deployment
- [ ] Run all tests
- [ ] Check code coverage
- [ ] Review security checklist
- [ ] Update documentation

### Database
- [ ] Run migrations on production
- [ ] Verify tables created
- [ ] Seed initial data if needed

### Environment Variables
- [ ] Set production Instagram credentials
- [ ] Configure production redirect URIs
- [ ] Set up monitoring keys

### Monitoring
- [ ] Set up error tracking (Sentry)
- [ ] Set up analytics (Mixpanel/Amplitude)
- [ ] Configure alerts

### Post-deployment
- [ ] Smoke test all endpoints
- [ ] Verify Instagram OAuth works
- [ ] Check analytics events
- [ ] Monitor error rates

---

## Documentation

- [ ] Update API documentation
- [ ] Add user guide for social features
- [ ] Document Instagram integration steps
- [ ] Create troubleshooting guide

---

## Launch Preparation

### Marketing
- [ ] Prepare announcement post
- [ ] Create tutorial videos
- [ ] Update app screenshots
- [ ] Write release notes

### Support
- [ ] Prepare FAQ
- [ ] Train support team
- [ ] Set up feedback channel

---

## Progress Tracker

| Phase | Status | Completion % |
|-------|--------|--------------|
| Backend Models | ⬜ | 0% |
| Backend Services | ⬜ | 0% |
| Backend API | ⬜ | 0% |
| Frontend API | ⬜ | 0% |
| Frontend Hooks | ⬜ | 0% |
| Frontend Components | ⬜ | 0% |
| Instagram Setup | ⬜ | 0% |
| Testing | ⬜ | 0% |
| Deployment | ⬜ | 0% |
| **Total** | ⬜ | **0%** |

---

Mark items as complete:
- [x] Completed item

Update progress as you go!
