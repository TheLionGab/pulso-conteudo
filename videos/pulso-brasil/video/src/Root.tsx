import React from 'react';
import {Composition} from 'remotion';
import {DUR,FPS,H,W} from './lib';
import {PulsoBrasil0411Soja} from './PulsoBrasil0411Soja';
export const RemotionRoot: React.FC = () => <Composition id="PulsoBrasil0411Soja" component={PulsoBrasil0411Soja} durationInFrames={Math.ceil(DUR*FPS)} fps={FPS} width={W} height={H}/>;
