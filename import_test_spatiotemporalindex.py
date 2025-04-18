import traceback

try:
    from src.indexing.combined_index import SpatioTemporalIndex
    print('SUCCESS: SpatioTemporalIndex imported')
except Exception as e:
    print('ERROR:', e)
    traceback.print_exc() 