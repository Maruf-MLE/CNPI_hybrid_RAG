import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from Cnpi_RAG.utils.key_manager import get_key_manager
km = get_key_manager()
print('Keys loaded:')
for k, l in km._keys:
    print(f'  {l}: {k[:12]}...{k[-4:]}')
print(f'Total: {len(km._keys)}')
