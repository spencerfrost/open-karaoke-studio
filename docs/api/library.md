# Library API (Artists & Albums)

API documentation for artist and album management. Most write operations are **admin-only**; the image/cover reads are public.

## Base URLs

```
/api/artists
/api/albums
```

For *browsing* artists and their songs, see the [Songs API](songs.md) (`GET /api/songs/artists`, `GET /api/songs/by-artist/{artist_name}`).

---

## Artist Endpoints

### Update Artist

Update an artist's display name. **Admin only.**

```http
PATCH /api/artists/{artist_id}
```

#### Request Body

```json
{
  "display_name": "The Beatles"
}
```

#### Response

```json
{
  "id": 1,
  "name": "the beatles",
  "display_name": "The Beatles"
}
```

---

### Delete Artist

Delete an artist. Songs exclusively credited to this artist are also deleted; songs shared with other artists only lose this artist's credit. **Admin only.**

```http
DELETE /api/artists/{artist_id}
```

---

### Get Artist Image

Fetch (and cache) an artist image from Discogs, served from local disk. Public.

```http
GET /api/artists/image?name={artist_name}
```

#### Response

JPEG image data, or `404` if no image could be found.

---

### Search Artist Image Candidates

Return Discogs image candidates for an artist without downloading them. **Admin only.**

```http
GET /api/artists/{artist_id}/images/search?q={query}
```

#### Response

```json
{
  "results": [ { "url": "https://...", "title": "..." } ]
}
```

---

### Set Artist Image

Download and save an artist image from a given URL. **Admin only.**

```http
POST /api/artists/{artist_id}/image
```

#### Request Body

```json
{
  "url": "https://..."
}
```

Returns `{ "success": true }`, or `422` if the download failed.

---

### Backfill Artist Images

Fetch images for all artists not yet checked, sequentially (respects Discogs rate limits). **Admin only.**

```http
POST /api/artists/images/backfill
```

#### Response

```json
{
  "fetched": 12,
  "not_found": 3,
  "errors": 0,
  "total": 15
}
```

---

### Split Artist Credits

Split a combined artist (e.g. `"A & B"`) into separate credits, applied to all songs currently linked to the artist. At least one `primary` credit is required. **Admin only.**

```http
POST /api/artists/{artist_id}/split-credits
```

#### Request Body

```json
{
  "credits": [
    { "name": "Artist A", "role": "primary" },
    { "name": "Artist B", "role": "featured" }
  ]
}
```

#### Response

```json
{
  "updated": 7
}
```

---

## Album Endpoints

### Get Album Cover

Serve the album's cover image. Song objects reference this via their `albumCoverUrl` field. Public.

```http
GET /api/albums/{album_id}/cover
```

#### Response

Binary image data, or `404` if the album has no cover.

---

## Usage Examples

```bash
# Get an album cover
curl http://localhost:5123/api/albums/12/cover -o cover.jpg

# Get an artist image by name
curl "http://localhost:5123/api/artists/image?name=Queen" -o artist.jpg

# Admin: rename an artist
curl -X PATCH http://localhost:5123/api/artists/1 \
  -H "Authorization: Bearer {admin-token}" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Queen"}'

# Admin: split a combined credit
curl -X POST http://localhost:5123/api/artists/42/split-credits \
  -H "Authorization: Bearer {admin-token}" \
  -H "Content-Type: application/json" \
  -d '{"credits": [{"name": "Simon", "role": "primary"}, {"name": "Garfunkel", "role": "primary"}]}'
```

---

## Related Documentation

- [Songs API](songs.md) - Artist browsing and song artist credits
- [Authentication API](authentication.md) - Admin authorization
