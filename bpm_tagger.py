import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import glob3 as glob
from pathlib import Path
import eyed3
import argparse
import re


class Tagger:
    def __init__(self, directory, overwrite_existing=False, print_res=False):
        self._directory = directory
        self._overwrite_existing = overwrite_existing
        self._print_res = print_res

        self.spotify = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials()
        )
        self.fnames = []
        self.tracks_artists = []
        self.uris = {}
        self.bpms = {}
        self.start_digit = False
        self.paths = []

    def get_info_from_id3(self):
        self.paths = [str(x) for x in Path(self._directory).rglob("*.mp3")]
        for path in self.paths:
            f = eyed3.load(path)
            if f.tag:
                # add file to list if there is no bpm or overwriting is True
                if not f.tag.bpm or self._overwrite_existing:
                    self.tracks_artists.append([f.tag.title, f.tag.artist])
            else:
                print(f"Unable to load {path.split('/')[-1]}")

    def get_fnames(self):
        """
        Unused -> replaced by get_info_from_id3
        """
        self.paths = list(Path(self._directory).rglob("*.mp3"))
        self.fnames = [str(path).split("/")[-1] for path in self.paths]
        if False in [path[0].isdigit() for path in self.fnames]:
            self.start_digit = False
        else:
            self.start_digit = True

    def get_tracks_artists(self):
        """
        Unused -> replaced by get_info_from_id3
        """
        for fname in self.fnames:
            if self.start_digit:
                _, lpart, rpart = fname.split("-", 2)
            else:
                lpart, rpart = fname.split("-", 1)
            artist = lpart.strip()
            track = rpart[:-4].strip()
            self.tracks_artists.append([track, artist])

    def get_uris(self):
        for (track, artist), path in zip(self.tracks_artists, self.paths):
            res = self.spotify.search(
                q=f"artist:{artist} track:{track}", type="track", limit=1
            )
            items = res["tracks"]["items"]
            if len(items) > 0:
                self.uris[path] = res["tracks"]["items"][0]["uri"]
            else:
                new_track_name, worked = re.subn(
                    r" *\(Original Mix\) *", r"", track
                )
                if worked:
                    res = self.spotify.search(
                        q=f"artist:{artist} track:{new_track_name}",
                        type="track",
                        limit=1,
                    )
                    items = res["tracks"]["items"]
                    if len(items) > 0:
                        self.uris[path] = res["tracks"]["items"][0]["uri"]
                    else:
                        print(f"Unable to find {track} - {artist} on Spotify")
                else:
                    print(f"Unable to find {track} - {artist} on Spotify")

    def get_bpms(self):
        for path, uri in self.uris.items():
            self.bpms[path] = self.spotify.audio_features([uri])[0]["tempo"]

    def _parse_filename(self, fname):
        lpart, rpart = fname.split("-")
        artist = lpart.strip()
        title = rpart[:-4].strip()
        return artist, title

    def write_bpms(self):
        for path, bpm in self.bpms.items():
            f = eyed3.load(path)
            f.tag.bpm = bpm
            f.tag.save()
            if self._print_res:
                print(f"Wrote {f.tag.bpm} as BPM to {path.split('/')[-1]}")

    def tag_directory(self):
        self.get_info_from_id3()
        print("Found", len(self.paths), "files")
        if not self._overwrite_existing:
            print(f"{len(self.paths) - len(self.tracks_artists)}/{len(self.paths)} already have a BPM")

        if len(self.tracks_artists):
            self.get_uris()
            print(f"Found {len(self.uris)}/{len(self.tracks_artists)} corresponding songs in spotify")
            self.get_bpms()
            self.write_bpms()
            print(f"Wrote BPMs to {len(self.uris)}/{len(self.tracks_artists)} files")
        print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--folder",
        type=str,
        default=None,
        help="Path of folder where bpms must be tagged"
    )
    parser.add_argument(
        "--overwrite",
        type=bool,
        default=False,
        help="If existing BPM's should be overwritten"
    )
    parser.add_argument(
        "--printres",
        type=bool,
        default=False,
        help="Print the BPM's found"
    )

    ARGS = parser.parse_args()

    if ARGS.folder:
        print(f"Adding BPM's to {ARGS.folder}")
        t = Tagger(ARGS.folder, ARGS.overwrite, ARGS.printres)
        t.tag_directory()
    else:
        print("usage: bmp_tagger.py --folder <path to folder>\n")
        print(
            "note: don't forget to export your SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET"
        )
