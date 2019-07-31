
# Import necessary libraries 
from pydub import AudioSegment

import io
from pydub import AudioSegment
from pydub.silence import split_on_silence
from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
import json
import queue
import os



class StreamGenerator:
    def __init__(self, filename):
        self.filename = filename
        self.chunks = queue.Queue()

    def get_stream(self):
        while not self.chunks.empty():
            yield self.chunks.get()
        return

    def process_audio(self):
        audio = AudioSegment.from_file(self.filename)
        counter = 1
        interval = 30 * 1000
        overlap = 1.5 * 1000
        end = 0

        # Flag to keep track of end of file.
        # When audio reaches its end, flag is set to 1 and we break
        flag = 0

        # Length of the audiofile in milliseconds
        n = len(audio)

        # Iterate from 0 to end of the file,
        # with increment = interval
        for i in range(0, 2 * n, interval):

            # During first iteration,
            # start is 0, end is the interval
            if i == 0:
                start = 0
                end = interval

            # All other iterations,
            # start is the previous end - overlap
            # end becomes end + interval
            else:
                start = end - overlap
                end = start + interval

            # When end becomes greater than the file length,
            # end is set to the file length
            # flag is set to 1 to indicate break.
            if end >= n:
                end = n

            chunk = audio[start:end]
            temp_file = file + str(counter) + ".wav"
            chunk.export(temp_file, format="wav")
            with io.open(temp_file, 'rb') as audio_file:
                content = audio_file.read()

            self.chunks.put(content)
            os.system("rm {}".format(temp_file))

            # Increment counter for the next chunk
            counter = counter + 1


class Transcription:

    def __init__(self):
        self.client = speech.SpeechClient()
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code='en-US',
            enable_word_time_offsets=True,
            model='video',
            diarization_speaker_count=2,
            enable_automatic_punctuation=True,
            use_enhanced=True,
            enable_speaker_diarization=True,
            speech_contexts=[speech.types.SpeechContext(phrases=[])]
        )

        self.streaming_config = types.StreamingRecognitionConfig(config=config)




    def transcribe_streaming(self, stream):
        """Streams transcription of the given audio file."""

        requests = (types.StreamingRecognizeRequest(audio_content=chunk)
                    for chunk in stream)


        # streaming_recognize returns a generator.
        return self.client.streaming_recognize(self.streaming_config, requests)


class ResponseHandler:
    def __init__(self, response):
        self.response = response

    def fetch_response(self):
        response_result = []
        for result in self.response.results:
            dict_result = {}
            dict_result['is_final'] = result.is_final
            dict_result['stability'] = result.stability
            alternatives = result.alternatives
            for alternative in alternatives:
                alternative_result = {}
                alternative_result['confidence'] = alternative.confidence
                alternative_result['transcript'] = alternative.transcript
                speakers = []
                for word in alternative.words:
                    speaker = {}
                    speaker[word.word] = word.speaker_tag
                    speakers.append(speaker)
                alternative_result['speakers'] = speakers
                dict_result['alternative_result'] = alternative_result
            response_result.append(dict_result)
        return response_result

def process_response(responses):
    output = ""
    current_speaker = None
    for response in responses:
        speakers = response['alternative_result']['speakers']
        for speaker in speakers:
            for word in speaker:
                if speaker[word] != current_speaker:
                    current_speaker = speaker[word]
                    output+="\n\nSpeaker-{}: ".format(current_speaker)
                output+= "{} ".format(word)
    return output




import sys
import traceback

file =  sys.argv[1]

final_output = []



f =  open(file+'.txt1', 'w+')

try:
    s = StreamGenerator(file)
    s.process_audio()
    stream = s.get_stream()
    import time
    start_time = time.time()
    print ("started transcription")
    while stream is not None:
        try:
            transcription = Transcription()
            generator = transcription.transcribe_streaming(stream)
            for response in generator:
                r = ResponseHandler(response).fetch_response()
                f.write(process_response(r))
                print (r)
                final_output.append(r)
        except:
            traceback.print_exc(file=sys.stdout)
    print("--- %s seconds ---" % (time.time() - start_time))

except:
    traceback.print_exc(file=sys.stdout)


f.close()

#add output to json file.
with open(file+'.json1', 'w') as f:
    json.dump(final_output, f)