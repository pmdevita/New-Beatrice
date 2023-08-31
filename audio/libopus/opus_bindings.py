from cffi import FFI

ffi = FFI()

ffi.cdef("""
    /* opus_defines.h */
    #define OPUS_OK ...
    #define OPUS_BAD_ARG ...
    #define OPUS_BUFFER_TOO_SMALL ...
    #define OPUS_INTERNAL_ERROR ...
    #define OPUS_INVALID_PACKET ...
    #define OPUS_UNIMPLEMENTED ...
    #define OPUS_INVALID_STATE ...
    #define OPUS_ALLOC_FAIL ...
    
    #define OPUS_APPLICATION_VOIP ...
    #define OPUS_APPLICATION_AUDIO ...
    #define OPUS_APPLICATION_RESTRICTED_LOWDELAY ...

    /* opus_types.h */
    typedef int16_t opus_int16;
    typedef uint16_t opus_uint16;
    typedef int32_t opus_int32;
    typedef uint32_t opus_uint32;
    
    /* opus.h */
    typedef ... OpusEncoder;
    int opus_encoder_get_size (int channels);
    OpusEncoder* opus_encoder_create(opus_int32 Fs, int	channels, int application, int * error);
    opus_int32 opus_encode (OpusEncoder * st, const opus_int16 * pcm, int frame_size, unsigned char * data, opus_int32 max_data_bytes);
    void opus_encoder_destroy(OpusEncoder * st);
""")

ffi.set_source("_py_opus", """
#include "opus.h"
""", libraries=['opus'])

# C = ffi.verify("#include \"opus.h\"", libraries=[str('opus')])

if __name__ == '__main__':
    ffi.compile(verbose=True)
