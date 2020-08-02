#!/usr/bin/python3

# Author: T. Junttila
# License: The MIT License

"""
A small Python script for making videos by
combining PDF and Amazon Polly narration.
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

import parser

voices = ['Zeina', 'Zhiyu', 'Naja', 'Mads', 'Lotte', 'Ruben', 'Nicole', 'Russell', 'Amy', 'Emma', 'Brian', 'Aditi', 'Raveena', 'Ivy', 'Joanna', 'Kendra', 'Kimberly', 'Salli', 'Joey', 'Justin', 'Matthew', 'Geraint', 'Céline', 'Celine', 'Léa', 'Mathieu', 'Chantal', 'Marlene', 'Vicki', 'Hans', 'Aditi', 'Dóra', 'Dora', 'Karl', 'Carla', 'Bianca', 'Giorgio', 'Mizuki', 'Takumi', 'Seoyeon', 'Liv', 'Ewa', 'Maja', 'Jacek', 'Jan', 'Camila', 'Vitória', 'Vitoria', 'Ricardo', 'Inês', 'Ines', 'Cristiano', 'Carmen', 'Tatyana', 'Maxim', 'Conchita', 'Lucia', 'Enrique', 'Mia', 'Lupe', 'Penélope', 'Penelope', 'Miguel', 'Astrid', 'Filiz', 'Gwyneth']
voices_neural = ['Amy', 'Emma', 'Brian', 'Ivy', 'Joanna', 'Kendra', 'Kimberly', 'Salli', 'Joey', 'Justin', 'Kevin', 'Matthew', 'Camila', 'Lupe']
voices_conversational = ['Joanna', 'Matthew', 'Lupe']

def millis_to_srt(millis):
    result = ''
    # milliseconds
    t = millis % 1000
    result = ('%03d' % t) + result
    millis -= t
    millis /= 1000
    # seconds
    t = millis % 60
    result = ('%02d,' % t) + result
    millis -= t
    millis /= 60
    # minutes
    t = millis % 60
    result = ('%02d:' % t) + result
    millis -= t
    millis /= 60
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
        r = execute(f'pdfinfo {args.pdf_file}')
        nof_pages = None
        for line in r.stdout.decode('utf-8').split('\n'):
            m = re.match('^Pages:\s*(\d+)\s*$', line)
            if m:
                nof_pages = int(m.group(1))
                break
        if nof_pages == None:
            error(f'Could not read the number of pages with "{cmd}"')
        pages = list(range(1, nof_pages+1))
        return pages
    # --pages parameter was given, parse it
    for comp in [c.strip() for c in args.pages.split(",")]:
        m = re.match(r'^(\d+)$', comp)
        if m:
            pages.append(int(m.group(1)))
            continue
        m = re.match(r'^(\d+)\s*-\s*(\d+)$', comp)
        if m:
            (start,end) = (int(m.group(1)), int(m.group(2)))
            length = end - start + 1
            if length > 0 and length < 10000:
                for i in range(start, end+1):
                    pages.append(i)
                continue
        error('Invalid page range component: '+comp)
    return pages

        
def read_scripts(script_file, error):
    """
    Read all the scripts from a file.
    """
    scripts = []
    script = []
    in_script = False
    try:
        with open(script_file, 'r') as f:
            for line in f.readlines():
                line = line.rstrip()
                if re.match(r'^#page\s*', line):
                    if in_script:
                        scripts.append(script)
                    in_script = True
                    script = []
                    continue
                if not in_script:
                    error('In the script file, all text should be after a "#page" block')
                script.append(line)
            if in_script:
                scripts.append(script)
    except IOError:
        error(f'Could not read the script file "{script_file}"')
    return scripts


def script_to_ssml_and_hash(script, args):
    """
    Transform a script to SSML.
    Return a hash of the voice, style, and the script as well for
    caching audio files produced by the TTS system.
    """
    
    h = hashlib.sha256()
    h.update(args.voice.encode('utf-8'))
    h.update(str(args.neural).encode('utf-8'))
    h.update(str(args.conversational).encode('utf-8'))
    plain = ''
    ssml = ''
    ssml += '<speak><break time="200ms" />'
    if args.conversational:
        ssml += '<amazon:domain name="conversational">'
    ssml += '\n'
    for line in script:
        ast = parser.parse_(line)
        l_ssml = ''.join([node.to_ssml(args.neural) for node in ast]) + '\n'
        ssml += l_ssml
        h.update(l_ssml.encode('utf-8')) 
    if args.conversational:
        ssml += '</amazon:domain>'
    ssml += '</speak>'
    ssml += '\n'
    return (ssml, h.hexdigest())



if __name__ == '__main__':
    p = argparse.ArgumentParser(formatter_class = argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('--voice', metavar='V', default='Joanna',
                   help='the applied TTS voice')
    p.add_argument('--neural', action='store_true',
                   help='use neural TTS')
    p.add_argument('--conversational', action='store_true',
                   help='use conversational style')
    p.add_argument('--aws_profile', metavar='P', default='PollyUser',
                   help='a Polly-enabled AWS profile')
    p.add_argument('--audio_cache', metavar='A', default='pdf2video-cache',
                   help='the directory for caching TTS audio files')
    p.add_argument('--temp_prefix', metavar='T', default='temp',
                   help='the prefix for the created temporary files')
    p.add_argument('--quiet', action='store_true',
                   help='do not print progress information')
    p.add_argument('--pages', metavar='P', default='all',
                   help='the page range of form "1,3,4-7,1"')
    #p.add_argument('--output', metavar='O', default='video.mp4',
    #               help="the output file")
    p.add_argument('pdf_file', help="the input PDF file")
    p.add_argument('script_file', help="the input script file")
    p.add_argument('output_file', help="the output mp4 video file")
    #p.add_argument('files', nargs=argparse.REMAINDER)
    args = p.parse_args()

    def verbose(s):
        if not args.quiet: print(s)
    
    temp_image_files = []
    temp_ssml_files = []
    temp_ts_files = []
    def unlink(file_name):
        try: os.unlink(file_name)
        except FileNotFoundError: pass
    def clean_temps():
        # remove the created temporary files
        for file_name in temp_image_files: unlink(file_name)
        for file_name in temp_ssml_files: unlink(file_name)
        for file_name in temp_ts_files: unlink(file_name)
    def error(msg):
        clean_temps()
        p.exit(1, msg+'\n')
    def execute(cmd):
        try:
            r = subprocess.run(re.split('\s+', cmd.strip()), stdout=PIPE, stderr=PIPE)
        except Exception as err:
            error(f'Error when executing "{cmd}".\n'+str(err))
        if r.returncode != 0:
            print(" ".join(r.args))
            error(f'Error when executing "{cmd}". The last 10 lines of the stderr output is as follows:\n' + '\n'.join((r.stderr.decode('utf-8').split('\n'))[-11:]))
        return r
    def make_dir(dir_name):
        if os.path.exists(dir_name):
            if not os.path.isdir(dir_name):
                error("Not a directory: "+dir_name)
        else: os.mkdir(dir_name)

    
    pages = parse_page_range(args, execute, error)
    
    # Check voice arguments consistency
    if args.voice not in voices:
        error(f'Unsupported voice {args.voice}. The available voices are {", ".join(voices)}.')
    if args.neural and args.voice not in voices_neural:
        error(f'voice {args.voice} is not available in neural TTS. The available neural voices are {", ".join(voices_neural)}.')
    if args.conversational:
        args.neural = True
        if args.voice not in voices_conversational:
            error(f'voice {args.voice} is not available in conversational style. The available conversational voices are {", ".join(voices_conversational)}.')

    scripts = read_scripts(args.script_file, error)

    make_dir(args.audio_cache)
    
    if len(scripts) != len(pages):
        error(f'{len(pages)} PDF pages selected but the script file contains {len(scripts)} scripts')


    # Select and convert selected pages to images
    for (index, page_num) in enumerate(pages):
        verbose(f'Extracting and converting PDF page {page_num}')
        image_file = f'{args.temp_prefix}-{index+1}'
        temp_image_files.append(image_file+".ppm")
        cmd = f'pdftoppm -scale-to-y 1080 -scale-to-x -1 -f {page_num} -singlefile {args.pdf_file} {image_file}'
        execute(cmd)

    # Make audio files with AWS Polly (cache the results)
    audio_files = []
    marks_files = []
    for (index, script) in enumerate(scripts):
        verbose('Making the audio track %d' % (index+1))
        (ssml, hash_hex) = script_to_ssml_and_hash(script, args)
        ssml_file = f'{args.temp_prefix}-{index+1}.ssml'
        temp_ssml_files.append(ssml_file)
        with open(ssml_file, "w") as f:
            f.write(ssml)
        audio_file = os.path.join(args.audio_cache, hash_hex+".mp3")
        marks_file = os.path.join(args.audio_cache, hash_hex+".mrk")
        if False:
            plain_file = os.path.join(args.audio_cache, hash_hex+".txt")
            with open(plain_file, "w") as f:
                f.write(plain)
        # Use Polly to generate the MP3 file if not in cache
        if os.path.isfile(audio_file):
            verbose('  Audio file found in cache')
        else:
            verbose('  Calling Polly for the audio file')
            cmd = f'aws --profile {args.aws_profile} polly synthesize-speech --text-type ssml --text file://{ssml_file} --output-format mp3 --voice-id {args.voice}'
            if args.neural: cmd += ' --engine neural'
            cmd += f' {audio_file}'
            execute(cmd)
        audio_files.append(audio_file)
        # Use Polly to generate the speech marks JSON file if not in cache
        if os.path.isfile(marks_file):
            verbose('  Speech marks found in cache')
        else:
            verbose('  Calling Polly for speech marks')
            cmd = f'aws --profile {args.aws_profile} polly synthesize-speech --text-type ssml --text file://{ssml_file} --output-format json --speech-mark-types sentence word viseme ssml  --voice-id {args.voice}'
            if args.neural: cmd += ' --engine neural'
            cmd += f' {marks_file}'
            execute(cmd)
        marks_files.append(marks_file)

    #
    # Make srt subtitles
    #
    for (index, script) in enumerate(scripts):
        # Read the speech marks
        marks_file = marks_files[index]
        marks = []
        with open(marks_file, 'r') as f:
            for line in f.readlines():
                mark = json.loads(line)
                if mark['type'] != 'word': continue
                if mark['value'].startswith('<break'): continue
                marks.append(mark)
        #print([m['value'] for m in marks])

        srts = []
        index = 0
        for line in script:
            if line.strip() == '': continue
            (dummy, words, sub) = parser.parse(line, args.neural)
            if len(words) == 0: continue
            #print(words[0])
            #print(marks)
            #print(marks[index])
            #print([m['value'] for m in marks[index:index+len(words)]])
            if words[0] != marks[index]['value'] and words[0][:-1] != marks[index]['value'] and words[0][1:] != marks[index]['value']:
                #print(words[0], marks[index]['value'])
                p.error(f'Subtitle synchronization failed: "{words[0]}" vs "{marks[index]["value"]}"')
            # For some reason, "5 seconds" is considered one work in Polly
            # so index_end = index + len(words) does not quite work
            index_end = index
            read = 0
            while read < len(words) and index_end < len(marks):
                read += len(re.split('\s+', marks[index_end]['value']))
                index_end += 1

            
            start = marks[index]['time']
            end = marks[index_end-1]['time']
            #end = marks[index+len(words)-1]['time']
            if len(srts) > 0:
                prev = srts[-1]
                prev['end'] = min(prev['end']+1000, start-10)
            srts.append({'start': start, 'end': end, 'text': sub})
            # For some reason, "5 seconds" is considered one work in Polly
            # so index += len(words) does not quite work
            #read = 0
            #while read < len(words) and index < len(marks):
            #    read += len(re.split('\s+', marks[index]['value']))
            #    index += 1
            index = index_end

        srt_file = marks_file[:-4] + '.srt'
        with open(srt_file, 'w') as f:
            for (index, srt) in enumerate(srts):
                f.write(f'{index+1}\n')
                f.write(millis_to_srt(srt['start'])+' --> '+millis_to_srt(srt['end'])+'\n')
                f.write(srt['text']+'\n')
                f.write('\n')
    
    # Combine images and audios to transport streams
    for (index, page_num) in enumerate(pages):
        verbose(f'Combining PDF page and audio: {index+1}')
        ts_file = f'{args.temp_prefix}-{index+1}.mp4'
        temp_ts_files.append(ts_file)
        audio_file = audio_files[index]
        cmd = f'ffmpeg -y -loop 1 -i {temp_image_files[index]} -i {audio_file} -shortest -c:v libx264 -vf scale=-2:1080,format=yuv420p -c:a copy -tune stillimage d{ts_file}'
        execute(cmd)
        verbose(f'  Adding subtitles')
        srt_file = audio_file[:-4] + '.srt'
        if os.stat(srt_file).st_size == 0:
            os.rename(f'd{ts_file}', f'{ts_file}')
        else:
            #ffmpeg -i infile.mp4 -i infile.srt -c copy -c:s mov_text outfile.mp4
            cmd = f'ffmpeg -y -i d{ts_file} -i {srt_file} -c copy -c:s mov_text -metadata:s:s:0 language=eng {ts_file}'
            execute(cmd)
            unlink(f'd{ts_file}')
        
    # Combine the transport streams
    verbose(f'Combining the transport streams to "{args.output_file}"')
    lst_file = f'{args.temp_prefix}.lst'
    with open(lst_file, 'w') as f:
        for ts_file in temp_ts_files:
            f.write(f'file {ts_file}\n')
    cmd = f'ffmpeg -y -f concat -i {lst_file} -c:v copy -c:a aac -c:s copy -strict -2 {args.output_file}'
    execute(cmd)
    clean_temps()
    exit(0)