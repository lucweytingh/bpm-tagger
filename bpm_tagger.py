import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import glob3 as glob
from pathlib import Path
import eyed3
import argparse
import re


class Tagger:
    def __init__(self, directory):
        self.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials()
        )
        self.directory = directory
        self.fnames = []
        self.tracks_artists = []
        self.uris = {}
        self.bpms = {}
        self.start_digit = False

    def get_fnames(self):
        paths = list(Path(self.directory).rglob("*.mp3"))
        self.fnames = [str(path).split("/")[-1] for path in paths]
        if False in [path[0].isdigit() for path in self.fnames]:
            self.start_digit = False
        else:
            self.start_digit = True

    def get_tracks_artists(self):
        for fname in self.fnames:
            if self.start_digit:
                _, lpart, rpart = fname.split("-", 2)
            else:
                lpart, rpart = fname.split("-", 1)
            artist = lpart.strip()
            track = rpart[:-4].strip()
            self.tracks_artists.append([track, artist])

    def get_uris(self):
        for (track, artist), fname in zip(self.tracks_artists, self.fnames):
            res = self.spotify.search(q=f"artist:{artist} track:{track}", type='track', limit=1)
            items = res['tracks']['items']
            if len(items) > 0:
                self.uris[fname] = res["tracks"]["items"][0]["uri"]
            else:
                new_track_name, worked = re.subn(r' *\(Original Mix\) *', r'', track)
                if worked:
                    res = self.spotify.search(q=f"artist:{artist} track:{new_track_name}", type='track', limit=1)
                    items = res['tracks']['items']
                    if len(items) > 0:
                        self.uris[fname] = res["tracks"]["items"][0]["uri"]
                    else:
                        print(f"Unable to find {track} - {artist} on Spotify")
                else:
                    print(f"Unable to find {track} - {artist} on Spotify")

    def get_bpms(self):
        for fname, uri in self.uris.items():
            self.bpms[fname] = self.spotify.audio_features([uri])[0]["tempo"]

    def _parse_filename(self, fname):
        lpart, rpart = fname.split("-")
        artist = lpart.strip()
        title = rpart[:-4].strip()
        return artist, title

    def write_bpms(self):
        for fname, bpm in self.bpms.items():
            f = eyed3.load(self.directory + "/" + fname)
            f.tag.bpm = bpm
            f.tag.save()
            print(f"Wrote {bpm} as BPM to {fname}")

    def tag_directory(self):
        self.get_fnames()
        print("Found:", len(self.fnames), "files")
        self.get_tracks_artists()
        self.get_uris()
        print("Found:", len(self.uris), "corresponding songs in spotify")
        self.get_bpms()
        self.write_bpms()
        print("Done!")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=str, default=None,
                        help="Path of folder where bpms must be tagged")
    ARGS = parser.parse_args()

    if ARGS.folder:
        print(f"Adding BPM's to {ARGS.folder}")
        t = Tagger(ARGS.folder)
        t.tag_directory()
    else:
        print("usage: bmp_tagger.py --folder <path to folder>\n")
        print("note: don't forget to export your SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET")
