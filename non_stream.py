
from google.cloud import storage
from google.cloud import speech_v1p1beta1  as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
import json


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    res = blob.upload_from_filename(source_file_name)

    print (res)

    print('File {} uploaded to {}.'.format(
        source_file_name,
        destination_blob_name))



def transcribe_gcs(gcs_uri, phrase_hints=[], language_code="en-US"):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""
    client = speech.SpeechClient()
    phrases = phrase_hints
    audio = types.RecognitionAudio(uri=gcs_uri)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_word_time_offsets=True,
        model = 'video',
        diarization_speaker_count=2,
        enable_automatic_punctuation=True,
        use_enhanced=True,
        enable_speaker_diarization=True,
        speech_contexts=[speech.types.SpeechContext(phrases=phrases)]
    )

    operation = client.long_running_recognize(config, audio)

    return operation.result(timeout=90000).results

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

blob = "temp/"+file

print("uploading")
upload_blob("speech-analysis-cn", file, blob)
print ("done")
import os
cloud_file = os.path.join('gs://', "speech-analysis-cn", blob)


final_output = []



f =  open(file+'.txt', 'w+')

try:
    import time
    start_time = time.time()
    response_generator = transcribe_gcs(cloud_file)
    for response in response_generator:
        r = ResponseHandler(response).fetch_response()
        f.write(process_response(r))
        final_output.append(r)
    print("--- %s seconds ---" % (time.time() - start_time))

except:
    traceback.print_exc(file=sys.stdout)

f.close()

#add output to json file.
with open(file+'.json', 'w') as f:
    json.dump(final_output, f)