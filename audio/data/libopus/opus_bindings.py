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
    
    #define OPUS_SET_COMPLEXITY_REQUEST ...
    #define OPUS_SET_BITRATE_REQUEST ...
    #define OPUS_SET_BANDWIDTH_REQUEST ...
    #define OPUS_SET_INBAND_FEC_REQUEST ...
    #define OPUS_SET_PACKET_LOSS_PERC_REQUEST ...
    #define OPUS_SET_SIGNAL_REQUEST ...
    
    #define OPUS_AUTO ...
    #define OPUS_SIGNAL_VOICE ...
    #define OPUS_SIGNAL_MUSIC ...

    #define OPUS_BANDWIDTH_FULLBAND ...
    #define OPUS_BANDWIDTH_MEDIUMBAND ...
    #define OPUS_BANDWIDTH_NARROWBAND ...
    #define OPUS_BANDWIDTH_SUPERWIDEBAND ...
    #define OPUS_BANDWIDTH_WIDEBAND ...
    
    /* Encoder encode errors */
    #define OPUS_OK ...
    #define OPUS_BAD_ARG ...
    #define OPUS_BUFFER_TOO_SMALL ...
    #define OPUS_INTERNAL_ERROR ...
    #define OPUS_INVALID_PACKET ...
    #define OPUS_UNIMPLEMENTED ...
    #define OPUS_INVALID_STATE ...
    #define OPUS_ALLOC_FAIL ...

    /* opus_types.h */
    typedef int16_t opus_int16;
    typedef uint16_t opus_uint16;
    typedef int32_t opus_int32;
    typedef uint32_t opus_uint32;
    
    /* opus.h */
    typedef ... OpusEncoder;
    int opus_encoder_get_size (int channels);
    OpusEncoder* opus_encoder_create(opus_int32 Fs, int	channels, int application, int * error);
    int opus_encode (OpusEncoder * st, const opus_int16 * pcm, int frame_size, unsigned char * data, int max_data_bytes);
    void opus_encoder_destroy(OpusEncoder * st);
    int opus_encoder_ctl ( OpusEncoder * st, int request, ...);
    
""")

ffi.set_source("_py_opus", """
#include "opus.h"
#include "opus_types.h"
""", libraries=['opus'])

# C = ffi.verify("#include \"opus.h\"", libraries=[str('opus')])

if __name__ == '__main__':
    ffi.compile(verbose=True)