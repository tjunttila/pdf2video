# Description

`pdf2video` is a Python script that combines

* (selected pages of) a [PDF](https://en.wikipedia.org/wiki/PDF) presentation, and
* a text script

into a video narrated by the [Amazon Polly](https://aws.amazon.com/polly/) text-to-speech engine.
It can be used to generate, for instance, educational videos.

Please see this [sample video](https://users.aalto.fi/tjunttil/pdf2video.mp4),
produced with the tool, for a short introduction.
Observe that some browsers don't show the subtitles embedded in MP4 videos,
please see this [sample video with WebVTT subtitles](https://users.aalto.fi/tjunttil/pdf2video.html) in such as case.

# Requirements

Using `pdf2video` requires the following external tools and services:

* [Python](https://www.python.org/) version 3.6 or later.
* The `pdfinfo` and `pdftoppm` command line tools provided in the [poppler PDF rendering library](https://poppler.freedesktop.org/).
  
  In Ubuntu Linux, you can install these with `sudo apt get poppler-utils`.
  
  For macOs, they are available at least from [Homebrew](https://brew.sh/) with `brew install poppler`.
* The `ffmpeg` command line tool from the [`FFmpeg`](https://ffmpeg.org/) framework.
  
  In Ubuntu Linux, you can install it with `sudo apt get ffmpeg`.
  
  For macOs, it is available at least from [Homebrew](https://brew.sh/) with `brew install ffmpeg`.
* Access to [Amazon Web Services](https://aws.amazon.com/).
* The [AWS Command Line Interface](https://aws.amazon.com/cli/) configured with a [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html) that can access the Polly service. To use the [neural voices](https://docs.aws.amazon.com/polly/latest/dg/ntts-voices-main.html) (recommended for the best quality), remember to select [a region in which they are supported](https://docs.aws.amazon.com/polly/latest/dg/NTTS-main.html).

# Installation

One can use `pip` to install `pdf2video` directly from GitHub:
```
python3 -m pip install git+https://github.com/tjunttila/pdf2video.git
```
See the [PyPA Installing Packages tutorial](https://packaging.python.org/tutorials/installing-packages/) for information on installing Python packages and on Python virtual environments.

# Usage

In the simplest case,
```
pdf2video presentation.pdf script.txt video.mp4
```
converts the PDF file  `presentation.pdf` and
the UTF-8 encoded script file `script.txt`
into the video `video.mp4` narrated by the default voice (Amazon Polly standard voice Joanna in the current version).
The video includes SRT subtitles that can be displayed by most video players.
In addition, for HTML use, [WebVTT subtitles](https://www.w3schools.com/tags/tag_track.asp) are produced in a separate file as well.

The selected PDF pages as well as the narration voice can be changed easily.
For instance, the [sample video](https://users.aalto.fi/tjunttil/pdf2video.mp4) was produced with the command
```
pdf2video sample.pdf sample.txt --pages "1,2,4-6" --voice Matthew --neural --conversational sample.mp4
```
All the options can be printed with `pdf2video --help`.

The script file is formatted as follows.
The script for each presentation page starts with a line `#page [name]` and
the following text then contains the script. The optional `[name]` parameter, that can be used in the `--only` option of the tool, is a string of ascii letters and underscores, possibly followed by a non-negative number. For instance `defs` and `example_3` are valid names.

A line starting with `%` is a comment and thus ignored.

In the script text, one can use the following modifiers:

* `*text*` to read `text` in an emphasized style,
* `@xyz@` to spell `xyz` as characters,
* `#slow/text/` to read `text` in a slower rate,
* `#high/text/` to use higher pitch for `text`,
* `#low/text/` to use lower pitch for `text`,
* `#n`, where `n` is a positive integer, to have a pause of length of `n`*100ms,
* `#ph/word/pronunciation/` spell the `word` with the [X-SAMPA](https://en.wikipedia.org/wiki/X-SAMPA) `pronunciation`, and
* `#sub/text/subtitle/` to use `subtitle` as the subtitle instead of the spoken `text`.

Above, the `/` delimiter can be any other symbol not occurring in the "arguments" of the modifier.
This allows one to nest modifiers.
For instance,
`#sub/big-#ph!Theta!Ti:.t@! of n/Θ(n)/`
reads as "big-theta of n" but shows as `Θ(n)` in the subtitles.

Please see the file [sample.txt](sample.txt) file for examples.


# Some good practices and hints

* Converting a script with many pages to video can take some time. For developing and debugging the script text, it is recommended to name the script pages with `#page pagename`, and then use the `--only` option of the tool to convert only the page under development.
* For pronunciations, one can find [IPA](https://en.wikipedia.org/wiki/International_Phonetic_Alphabet) pronunciations in many online dictionaries, and then convert them to X-SAMPA by using the table in the [X-SAMPA Wikipedia page](https://en.wikipedia.org/wiki/X-SAMPA).
* Whenever possible, avoid using the `@xyz@` construct as it seems to change the pitch of the whole sentence.


# License

The `pdf2video` tool is relased under the [MIT License](https://opensource.org/licenses/MIT).
