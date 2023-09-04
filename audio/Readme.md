## Atsume Audio

This is an implementation of a Discord audio bot written in Python. It's based on the original 
[audio implementation](https://github.com/pmdevita/Beatrice) from old Beatrice. It's also the 
only implementation of an audio bot for Hikari in Python as far as I know. It achieves good 
performance through a heavy use of async for IO and Numpy for audio mixing.

At the moment, it's still in the middle of porting but on completion, it will have the 
same multi-channel audio system as the original and some performance improvements
(processing time has already been cut in half!). It should also be more stable and less 
error prone now that everything is statically typed. Hopefully, this will be compilable
to C in the future with the mypyc compiler.

My hope is that this provides more flexibility, extensibility, and ease of start up 
and use than competing options.

