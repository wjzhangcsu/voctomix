#!/usr/bin/env python3
import logging
from abc import ABCMeta, abstractmethod

from lib.config import Config


class AVSource(object, metaclass=ABCMeta):

    def __init__(self, name, outputs=None, has_audio=True, has_video=True,
                 force_num_streams=None):
        if not self.log:
            self.log = logging.getLogger('AVSource[{}]'.format(name))

        if outputs is None:
            outputs = [name]

        assert has_audio or has_video

        self.name = name
        self.has_audio = has_audio
        self.has_video = has_video
        self.outputs = outputs
        self.force_num_streams = force_num_streams
        self.pipe = ""

    def __str__(self):
        return 'AVSource[{name}]'.format(
            name=self.name
        )

    def attach(self, pipeline):
        return

    def build_pipeline(self, pipeline):
        self.pipe = pipeline
        if self.has_audio:
            num_streams = self.force_num_streams
            if num_streams is None:
                num_streams = Config.getint('mix', 'audiostreams')

            for audiostream in range(0, num_streams):
                audioport = self.build_audioport(audiostream)
                if not audioport:
                    continue

                self.pipe += """
{audioport}
! {acaps}
! queue
! tee
    name=audio-{name}-{audiostream}
                """.format(
                    audioport=audioport,
                    audiostream=audiostream,
                    acaps=Config.get('mix', 'audiocaps'),
                    name=self.name
                )

                for output in self.outputs:
                    pipeline += """
audio-{name}-{audiostream}.
! queue
! interaudiosink
    channel=audio-{output}-{audiostream}
                    """.format(
                        output=output,
                        audiostream=audiostream,
                        name=self.name
                    )

        if self.has_video:
            self.pipe += """
{videoport}
! {vcaps}
! queue
! tee
    name=video-{name}
            """.format(
                videoport=self.build_videoport(),
                name=self.name,
                vcaps=Config.get('mix', 'videocaps')
            )

            for output in self.outputs:
                pipeline += """
video-{name}.
! queue
! video-{output}
                """.format(name=self.name, output=output)

    def build_deinterlacer(self):
        deinterlace_config = self.get_deinterlace_config()

        if deinterlace_config == "yes":
            return "videoconvert ! yadif mode=interlaced"

        elif deinterlace_config == "assume-progressive":
            return "capssetter " \
                   "caps=video/x-raw,interlace-mode=progressive"

        elif deinterlace_config == "no":
            return ""

        else:
            raise RuntimeError(
                "Unknown Deinterlace-Mode on source {} configured: {}".
                format(self.name, deinterlace_config))

    def get_deinterlace_config(self):
        section = 'source.{}'.format(self.name)
        deinterlace_config = Config.get(section, 'deinterlace', fallback="no")
        return deinterlace_config

    @abstractmethod
    def build_audioport(self, audiostream):
        raise NotImplementedError(
            'build_audioport not implemented for this source')

    @abstractmethod
    def build_videoport(self):
        raise NotImplementedError(
            'build_videoport not implemented for this source')

    @abstractmethod
    def restart(self):
        raise NotImplementedError('Restarting not implemented for this source')
