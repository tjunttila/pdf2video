#!/usr/bin/python3

"""
A small Python script for making videos by
combining PDF and Amazon Polly narration.
Author: T. Junttila
License: The MIT License
Requires:
- pdfinfo
- pdftoppm
- ffmpeg
- access to Amazon Web Services with a Polly-enabled profile
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
from subprocess import PIPE
import sys

from .parser import parse_to_ast, parse

voices = ['Zeina', 'Zhiyu', 'Naja', 'Mads', 'Lotte', 'Ruben', 'Nicole',
          'Russell', 'Amy', 'Emma', 'Brian', 'Aditi', 'Raveena', 'Ivy',
          'Joanna', 'Kendra', 'Kimberly', 'Salli', 'Joey', 'Justin',
          'Matthew', 'Geraint', 'Céline', 'Celine', 'Léa', 'Mathieu',
          'Chantal', 'Marlene', 'Vicki', 'Hans', 'Aditi', 'Dóra', 'Dora',
          'Karl', 'Carla', 'Bianca', 'Giorgio', 'Mizuki', 'Takumi', 'Seoyeon',
          'Liv', 'Ewa', 'Maja', 'Jacek', 'Jan', 'Camila', 'Vitória', 'Vitoria',
          'Ricardo', 'Inês', 'Ines', 'Cristiano', 'Carmen', 'Tatyana', 'Maxim',
          'Conchita', 'Lucia', 'Enrique', 'Mia', 'Lupe', 'Penélope',
          'Penelope', 'Miguel', 'Astrid', 'Filiz', 'Gwyneth']

voices_neural = ['Amy', 'Emma', 'Brian', 'Ivy', 'Joanna', 'Kendra',
                 'Kimberly', 'Salli', 'Joey', 'Justin', 'Kevin', 'Matthew',
                 'Camila', 'Lupe']

voices_conversational = ['Joanna', 'Matthew', 'Lupe']

def millis_to_srt(millis):
    """Convert milliseconds time to the SRT subtitles format time string."""
    result = ''
    # milliseconds
    milliseconds = millis % 1000
    result = ('%03d' % milliseconds) + result
    millis = (millis - milliseconds) / 1000
    # seconds
    seconds = millis % 60
    result = ('%02d,' % seconds) + result
    millis = (millis - seconds) / 60
    # minutes
    minutes = millis % 60
    result = ('%02d:' % minutes) + result
    millis = (millis - minutes) / 60
    # hours
    result = ('%02d:' % millis) + result
    # ready
    return result


def parse_page_range(args, execute, error):
    """
    Parse the page range.
    """
    pages = []
    if args.pages == 'all':
        # --pages parameter was not given
        # Use pdfinfo to find out the number of pages, select all
        cmd = f'{args.pdfinfo} {args.pdf_file}'
        exec_result = execute(cmd)
        nof_pages = None
        for line in exec_result.stdout.decode('utf-8').split('\n'):
            match = re.match(r'^Pages:\s*(\d+)\s*$', line)
            if match:
                nof_pages = int(match.group(1))
                break
        if nof_pages is None:
            error(f'Could not read the number of pages with "{cmd}"')
        pages = list(range(1, nof_pages+1))
        return pages
    # --pages parameter was given, parse it
    for comp in [c.strip() for c in args.pages.split(",")]:
        match = re.match(r'^(\d+)$', comp)
        if match:
            pages.append(int(match.group(1)))
            continue
        match = re.match(r'^(\d+)\s*-\s*(\d+)$', comp)
        if match:
            (start,end) = (int(match.group(1)), int(match.group(2)))
            length = end - start + 1
            if 0 < length < 10000:
                for i in range(start, end+1):
                    pages.append(i)
                continue
        error('Invalid page range component: '+comp)
    return pages


def parse_only(args, scripts, scripts_names, error):
    """
    Parse the 'only' range.
    """
    only = set()
    if args.only == 'the full set':
        # --only parameter was not given
        # Include all the #pages
        for i in range(0, len(scripts)):
            only.add(i)
        return only
    # --only parameter was given, parse it
    for comp in [c.strip() for c in args.only.split(",")]:
        # Single number
        match = re.match(r'^[1-9]\d*$', comp)
        if match:
            num = int(match.group(0))
            if not num <= len(scripts):
                error(f'#page {num} was selected in --only, ' \
                      f'but only {len(scripts)} #pages exists')
            only.add(num-1)
            continue
        # Numeric range
        match = re.match(r'^([1-9]\d*)\s*-\s*([1-9]\d*)$', comp)
        if match:
            (start,end) = (int(match.group(1)), int(match.group(2)))
            length = end - start + 1
            if 0 < length < 10000:
                for num in range(start, end+1):
                    if not num <= len(scripts):
                        error(f'#page {num} was selected in --only, ' \
                              f'but only {len(scripts)} #pages exists')
                    only.add(num-1)
                continue
        # Single name
        match = re.match(r'^[a-zA-Z_]+([1-9]\d*)?$', comp)
        if match:
            name = match.group(0)
            if name not in scripts_names:
                error(f'#page named "{name}" was selected in --only, ' \
                      f'but there is no #page with that name. ' \
                      f'Available #page names are: ' \
                      f'{",".join(sorted(scripts_names.keys()))}')
            only.add(scripts_names[name])
            continue
        # name range
        match = re.match(r'^([a-zA-Z_]+)([1-9]\d*)-([1-9]\d*)$', comp)
        if match:
            (base,start,end) = (match.group(1),int(match.group(2)),int(match.group(3)))
            length = end - start + 1
            if 0 < length < 10000:
                for i in range(start, end+1):
                    name = base+str(i)
                    if name not in scripts_names:
                        error(f'#page named "{name}" was selected in --only, ' \
                              f'but there is no #page with that name. ' \
                              f'Available #page names are: ' \
                              f'{",".join(sorted(scripts_names.keys()))}')
                    only.add(scripts_names[name])
                continue
        error('Invalid "only" range component: '+comp)
    return only


def read_scripts(script_file, error):
    """
    Read all the scripts from a file.
    """
    scripts = []
    scripts_names = {}
    script = []
    in_script = False
    in_script_name = None
    try:
        with open(script_file, 'r', encoding='utf-8') as file_object:
            linenum = 0
            def err(msg):
                error(f'on line {linenum}: {msg}')
            for line in file_object.readlines():
                line = line.rstrip()
                linenum += 1
                if line == '':
                    # Ignore empty lines
                    continue
                if re.match(r'^%', line):
                    # Lines starting with % are comments, skip them
                    continue
                # A "#page" line starting a new page?
                match = re.match(r'^#page\s*(?P<name>\s+[a-zA-Z_]+([1-9]\d*)?)?\s*$', line)
                if match:
                    if in_script:
                        # The previous #page script is now fully read, save it
                        if in_script_name is not None:
                            if in_script_name in scripts_names:
                                err(f'#page named "{in_script_name}" defined twice')
                            scripts_names[in_script_name] = len(scripts)
                        scripts.append(script)
                    #print(m)
                    name = match['name']
                    #print(name)
                    in_script_name = name.strip() if name is not None else None
                    in_script = True
                    script = []
                    continue
                if line.startswith("#page"):
                    err("Malformed #page line: "+line)
                if not in_script:
                    err('In the script file, all text should be after a "#page" block')
                # Add the line to the current page
                script.append((line, linenum))
            # All lines read, add the last page
            if in_script:
                if in_script_name is not None:
                    if in_script_name in scripts_names:
                        err(f'#page named "{in_script_name}" defined twice')
                    scripts_names[in_script_name] = len(scripts)
                scripts.append(script)
    except IOError:
        error(f'Could not read the script file "{script_file}"')
    return (scripts, scripts_names)


def script_to_ssml_and_hash(script, args):
    """
    Transform a script to SSML.
    Also returns a hash of the voice, style, and the script
    for caching audio files produced by the TTS system.
    """

    hash_value = hashlib.sha256()
    hash_value.update(args.voice.encode('utf-8'))
    hash_value.update(str(args.neural).encode('utf-8'))
    hash_value.update(str(args.conversational).encode('utf-8'))
    ssml = ''
    ssml += '<speak><break time="200ms" />'
    if args.conversational:
        ssml += '<amazon:domain name="conversational">'
    ssml += '\n'
    for (page_linenum, (line,linenum)) in enumerate(script):
        ast = parse_to_ast(line, linenum)
        l_ssml = ''
        # Start-of-the-line marks for subtitle synchronization
        l_ssml += f'<mark name="s{page_linenum}"/>'
        # Line contents in SSML
        l_ssml += ''.join([node.to_ssml(args.neural) for node in ast])+'\n'
        # End-of-the-line marks for subtitle synchronization
        l_ssml += f'<mark name="e{page_linenum}"/>'
        ssml += l_ssml
        hash_value.update(l_ssml.encode('utf-8'))
    if args.conversational:
        ssml += '</amazon:domain>'
    ssml += '</speak>'
    ssml += '\n'
    return (ssml, hash_value.hexdigest())


def main():
    """The main routine."""
    description = 'A tool for converting PDF presentations into ' \
                  'narrated videos. Please see ' \
                  'https://github.com/tjunttila/pdf2video/ for more details.'
    argp = argparse.ArgumentParser(
        formatter_class = argparse.ArgumentDefaultsHelpFormatter,
        description = description)
    argp.add_argument('--voice', metavar='V', default='Joanna',
                   help='the applied TTS voice')
    argp.add_argument('--neural', action='store_true',
                   help='use neural TTS')
    argp.add_argument('--conversational', action='store_true',
                   help='use conversational style')
    argp.add_argument('--aws_profile', metavar='A', default='default',
                   help='a Polly-enabled AWS profile')
    argp.add_argument('--audio_cache', metavar='C', default='pdf2video-cache',
                   help='the directory for caching TTS audio files')
    argp.add_argument('--temp_prefix', metavar='T', default='pdf2video-temp',
                   help='the prefix for the created temporary files')
    argp.add_argument('--ignore_subtitles', action='store_true',
                   help='do not include or produce subtitles')
    argp.add_argument('--quiet', action='store_true',
                   help='do not print progress information')
    argp.add_argument('--pages', metavar='P', default='all', help=
                   'The PDF page range of the form "1,3,4-7,1". ' \
                   'Defines the mapping from the #page texts ' \
                   'in the script file to selected PDF pages.')
    argp.add_argument('--only', metavar='O', default='the full set',
                   help = 'Only compile the selected #page texts. ' \
                   'Used mainly during the development to select some of ' \
                   'the #pages. A comma-sepated set of #page identifies, ' \
                   'which can be (i) numbers, (ii) #page names, or ' \
                   '(iii) ranges of of those. Example: "1,usage,scripts_1-2" ' \
                   'compiles the first #page, the ones named usage, '\
                   'scripts_1, and scripts_2.')
    #argp.add_argument('--output', metavar='O', default='video.mp4',
    #               help="the output file")
    argp.add_argument('--ffmpeg', default='ffmpeg',
                   help='the FFmpeg command line tool executable')
    argp.add_argument('--pdfinfo', default='pdfinfo',
                   help='the "pdfinfo" executable from Poppler utils')
    argp.add_argument('--pdftoppm', default='pdftoppm',
                   help='the "pdftoppm" executable from Poppler utils')
    argp.add_argument('pdf_file', help="the input PDF file")
    argp.add_argument('script_file', help="the input script file")
    argp.add_argument('output_file', help="the output mp4 video file")
    #argp.add_argument('files', nargs=argparse.REMAINDER)
    args = argp.parse_args()

    def verbose(msg):
        if not args.quiet:
            print(msg)

    temp_image_files = []
    temp_ssml_files = []
    temp_ts_files = []
    def unlink(file_name):
        if file_name is None:
            return
        try:
            os.unlink(file_name)
        except FileNotFoundError:
            pass
    def clean_temps():
        # remove the created temporary files
        for file_name in temp_image_files:
            unlink(file_name)
        for file_name in temp_ssml_files:
            unlink(file_name)
        for file_name in temp_ts_files:
            unlink(file_name)

    def error(msg):
        clean_temps()
        argp.exit(1, msg+'\n')

    def execute(cmd):
        try:
            exec_result = subprocess.run(re.split(r'\s+', cmd.strip()),
                                         stdout=PIPE, stderr=PIPE, check=False)
        except Exception as err:
            error(f'Error when executing "{cmd}".\n'+str(err))
        if exec_result.returncode != 0:
            #print(" ".join(r.args))
            error(f'Error when executing "{cmd}". The last 10 lines of ' \
                  f'the stderr output is as follows:\n' +
                  '\n'.join((exec_result.stderr.decode('utf-8').split('\n'))[-11:]))
        return exec_result

    def make_dir(dir_name):
        if os.path.exists(dir_name):
            if not os.path.isdir(dir_name):
                error("Not a directory: "+dir_name)
        else: os.mkdir(dir_name)


    if not args.output_file.endswith(".mp4"):
        error("The output file name must end with .mp4")

    pages = parse_page_range(args, execute, error)

    # Check voice arguments consistency
    if args.voice not in voices:
        error(f'Unsupported voice {args.voice}. The available voices are {", ".join(voices)}.')
    if args.neural and args.voice not in voices_neural:
        error(f'The voice {args.voice} is not available in neural TTS. ' \
              f'The available neural voices are {", ".join(voices_neural)}.')
    if args.conversational:
        args.neural = True
        if args.voice not in voices_conversational:
            error(f'The voice {args.voice} is not available in ' \
                  f'conversational style. The available conversational ' \
                  f'voices are {", ".join(voices_conversational)}.')

    (scripts, scripts_names) = read_scripts(args.script_file, error)

    make_dir(args.audio_cache)

    if len(scripts) != len(pages):
        error(f'{len(pages)} PDF pages selected but the script file ' \
              f'contains {len(scripts)} scripts')

    only = parse_only(args, scripts, scripts_names, error)

    # Select and convert selected pages to images
    for (index, page_num) in enumerate(pages):
        if index not in only:
            temp_image_files.append(None)
            continue
        verbose(f'Extracting and converting PDF page {page_num}')
        image_file = f'{args.temp_prefix}-{index+1}'
        temp_image_files.append(image_file+".ppm")
        cmd = f'{args.pdftoppm} -scale-to-y 1080 -scale-to-x -1 ' \
              f'-f {page_num} -singlefile {args.pdf_file} {image_file}'
        execute(cmd)

    # Make audio files with AWS Polly (cache the results)
    audio_files = []
    marks_files = []
    profile_arg = '' if args.aws_profile == 'default' else f'--profile {args.aws_profile}'
    for (index, script) in enumerate(scripts):
        if index not in only:
            temp_ssml_files.append(None)
            audio_files.append(None)
            marks_files.append(None)
            continue
        #
        # Audio track
        #
        verbose('Making the audio track %d' % (index+1))
        (ssml, hash_hex) = script_to_ssml_and_hash(script, args)
        ssml_file = f'{args.temp_prefix}-{index+1}.ssml'
        temp_ssml_files.append(ssml_file)
        with open(ssml_file, "w", encoding='utf-8') as file_handle:
            file_handle.write(ssml)
        audio_file = os.path.join(args.audio_cache, hash_hex+".mp3")
        marks_file = os.path.join(args.audio_cache, hash_hex+".mrk")
        # Use Polly to generate the MP3 file if not in cache
        if os.path.isfile(audio_file):
            verbose('  Audio file found in cache')
        else:
            verbose('  Calling Polly for the audio file')
            cmd = f'aws {profile_arg} polly synthesize-speech ' \
                  f'--text-type ssml --text file://{ssml_file} ' \
                  f'--output-format mp3 --voice-id {args.voice}'
            if args.neural:
                cmd += ' --engine neural'
            cmd += f' {audio_file}'
            execute(cmd)
        audio_files.append(audio_file)
        #
        # Speech marks for subtitles
        #
        if not args.ignore_subtitles:
            # Use Polly to generate the speech marks JSON file if not in cache
            if os.path.isfile(marks_file):
                verbose('  Speech marks found in cache')
            else:
                verbose('  Calling Polly for speech marks')
                cmd = f'aws {profile_arg} polly synthesize-speech ' \
                      f'--text-type ssml --text file://{ssml_file} ' \
                      f'--output-format json ' \
                      f'--speech-mark-types sentence word viseme ssml ' \
                      f'--voice-id {args.voice}'
                if args.neural:
                    cmd += ' --engine neural'
                cmd += f' {marks_file}'
                execute(cmd)
            marks_files.append(marks_file)

    if not args.ignore_subtitles:
        #
        # Make srt subtitles
        #
        for (index, script) in enumerate(scripts):
            if index not in only:
                continue
            # Read the speech marks, keep only the start and end-of-the-line marks
            marks_file = marks_files[index]
            starts = {}
            ends = {}
            with open(marks_file, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    mark = json.loads(line)
                    if mark['type'] != 'ssml':
                        continue
                    match = re.match(r'^s(?P<num>\d+?)$', mark['value'])
                    if match:
                        starts[int(match['num'])] = mark['time']
                    match = re.match(r'^e(?P<num>\d+?)$', mark['value'])
                    if match:
                        ends[int(match['num'])] = mark['time']
            #print(starts)
            #print(ends)
            srts = []
            for (page_linenum, (line, _)) in enumerate(script):
                #print(page_linenum, line)
                if line.strip() == '':
                    continue
                start = starts[page_linenum]
                end = ends[page_linenum]
                (dummy, words, sub) = parse(line, args.neural)
                if len(words) == 0:
                    continue
                srts.append({'start': start, 'end': end, 'text': sub})

            srt_file = marks_file[:-4] + '.srt'
            with open(srt_file, 'w', encoding='utf-8') as f:
                for (srt_index, srt) in enumerate(srts):
                    f.write(f'{srt_index+1}\n')
                    f.write(millis_to_srt(srt['start'])+' --> '+millis_to_srt(srt['end'])+'\n')
                    f.write(srt['text']+'\n')
                    f.write('\n')

    # Combine images and audios to transport streams
    for (index, page_num) in enumerate(pages):
        if index not in only:
            continue
        verbose(f'Combining PDF page and audio: {index+1}')
        ts_file = f'{args.temp_prefix}-{index+1}.mp4'
        temp_ts_files.append(ts_file)
        audio_file = audio_files[index]
        cmd = f'{args.ffmpeg} -y -loop 1 -i {temp_image_files[index]} ' \
              f'-i {audio_file} -shortest -c:v libx264 ' \
              f'-vf scale=-2:1080,format=yuv420p -c:a copy ' \
              f'-tune stillimage d{ts_file}'
        execute(cmd)
        if args.ignore_subtitles:
            os.rename(f'd{ts_file}', f'{ts_file}')
        else:
            verbose('  Adding subtitles')
            srt_file = audio_file[:-4] + '.srt'
            if os.stat(srt_file).st_size == 0:
                os.rename(f'd{ts_file}', f'{ts_file}')
            else:
                cmd = f'{args.ffmpeg} -y -i d{ts_file} -i {srt_file} ' \
                      f'-c copy -c:s mov_text -metadata:s:s:0 language=eng ' \
                      f'{ts_file}'
                execute(cmd)
                unlink(f'd{ts_file}')

    # Combine the transport streams
    verbose(f'Combining the transport streams to "{args.output_file}"')
    lst_file = f'{args.temp_prefix}.lst'
    with open(lst_file, 'w', encoding='utf-8') as f:
        for ts_file in temp_ts_files:
            f.write(f'file {ts_file}\n')
    cmd = f'{args.ffmpeg} -y -f concat -i {lst_file} -c:v copy -c:a aac ' \
          f'-c:s copy -strict -2 {args.output_file}'
    execute(cmd)

    if not args.ignore_subtitles:
        # Produce the WebVTT subtitles (for HTML)
        vtt_file = args.output_file[:-4]+'.vtt'
        verbose(f'Producing WebVTT subtitles at "{vtt_file}"')
        cmd = f'{args.ffmpeg} -y -i {args.output_file} {vtt_file}'
        execute(cmd)

    clean_temps()
    sys.exit(0)


if __name__ == '__main__':
    main()
