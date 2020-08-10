# Description

`pdf2video.py` is a Python script that combines

* (selected pages of) a [PDF](https://en.wikipedia.org/wiki/PDF) presentation, and
* a text script

into a video narrated by the [Amazon Polly](https://aws.amazon.com/polly/) text-to-speech engine.
It can be used to generate, for instance, educational videos.

Please see this [sample video](https://users.aalto.fi/tjunttil/pdf2video.mp4),
produced with the tool, for a short introduction.

# Requirements

Using `pdf2video.py` requires the following external tools and services:

* [Python](https://www.python.org/) version 3.5 or later.
* The `pdfinfo` and `pdftoppm` command line tools provided in the [poppler PDF rendering library](https://poppler.freedesktop.org/). In Ubuntu Linux, you can install these with `sudo apt get poppler-utils`.
* The `ffmpeg` command line tool from the [`FFmpeg`](https://ffmpeg.org/) framework. In Ubuntu Linux, you can install these with `sudo apt get ffmpeg`.
* Access to [Amazon Web Services](https://aws.amazon.com/).
* The [AWS Command Line Interface](https://aws.amazon.com/cli/) configured with a [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html) that can access the Polly service. To use the [neural voices](https://docs.aws.amazon.com/polly/latest/dg/ntts-voices-main.html) (recommended for the best quality), remember to select [a region in which they are supported](https://docs.aws.amazon.com/polly/latest/dg/NTTS-main.html).

# Usage

In the simplest case,
```
python3 pdf2video.py presentation.pdf script.txt video.mp4
```
converts the PDF file  `presentation.pdf` and the script `script.txt` into
the video `video.mp4` narrated by the default voice (Amazon Polly standard voice Joanna in the current version).
The video includes SRT subtitles that can be displayed by most video players.
In addition, for HTML use, [WebVTT subtitles](https://www.w3schools.com/tags/tag_track.asp) are produced in a separate file as well.

The selected PDF pages as well as the narration voice can be changed easily.
For instance, the [sample video](https://users.aalto.fi/tjunttil/pdf2video.mp4) was produced witth the command
```
python3 pdf2video.py sample.pdf sample.txt --pages "1,2,4-6" --voice Matthew --neural --conversational sample.mp4
```
All the options can be printed with `python3 pdf2video.py --help`.

The script file is formatted as follows.
The script for each presentation page starts with a line `#page` and
the following text then contains the script.
In the script text, one can use

* `*text*` to read `text` in an emphasized style,
* `@xyz@` to spell `xyz` as characters,
* `#high/text/` to use higher pitch for `text`,
* `#low/text/` to use lower pitch for `text`,
* `#n`, where `n` is a positive integer, to have a pause of length of `n`*100ms,
* `#ph/word/pronunciation/` spell the `word` with the [X-SAMPA](https://en.wikipedia.org/wiki/X-SAMPA) `pronunciation`, and
* `#sub/text/subtitle/` to use `subtitle` as the subtitle instead of the spoken `text`,

Please see the file [sample.txt](sample.txt) file for examples.

# License

The `pdf2video.py` tool is relased under the [MIT License](https://opensource.org/licenses/MIT).
