import os, json, base64, zlib
PAYLOAD = 'eJytV/9P6zYQ/1e8DInHNpK2gx/KK9GgsA2JCfRgmiZFitz4mvrVsSPbKWSI/33nJP1Cm+7Rsh+qxvb57nPffHcvHut040IWpqAi1mqkrPHOyItXf/r22eLS+9OAPqYpSHtG7i5ujh+A6mRyqWwkh5o+iWMGgpZnpNuJ5BU3VAj1dEaCXPMZtfBmz3v9iaDQXmxoBjFy5LasJHLJ4Nmf2Ew4iYNJN3zIIeFUkHtB5SDAjYHJqSTcQpZrlZ9HHgpIIPLCft/v9weBOw4HeXiRWFRHlEhKEmWsIQfdk5okDz2Uv127HyJ5sY6U8fE4RomsSBrrbGK9pIYnS5DhQbczx4N791qtnp3Oz3bHkilpJ6KMqZSo4jbDFSOTaJ5brhrD5QgBTXWGhugEFQ+itFt0ghJ9uZ9dZlRzKrea5GHCtZ2L/wLMCT91knB5KQoHptfZXTJgwGpAaTpWUrTGzkixMhwE9V9tiZCppMiQoe92fS4l6N8f/7jFIHJYr0pJs7kD83CoMnQPBvRFkgEZKp07nJH3Gf1Ws9sd86RkGpOBYSSBQao24IzPCGeIieY5hnVlRUvtEtgVtbQyYYCkm7qlYK8FuM/L8oZ9avgcbajbzvQj+vXiMa2yLpZKxhaeW/VrRJtaMs9SYnSCmJIJ1dbPZYpK7y6ZQaLQtHwGW2T+BSJRGaxLxRRMQPspH0cecbF8POGMgcQjqwvYGUuKWNxFTFLWnpt1RC68XNGhbK0E4JLhY6fSOZbqcAllJa9HjSaUTDSMkeR7PB8KZXCfzkOjjv7dFXDuGwmVTLlM91dhZ7gZ5XKFJBBcTpHsFv9qqppgX63GmCEGnUPzd+jkyJwKS8BdXHYrHMu9Hu71VjT4Zi7WbI98ytj1DLdvubGAeYlHUyiZepIRKgbn4QsffwIf987PUdAjHeEtAj6+G+7aFYxpIeyno8+vR8t83dMyPzubsFjSWZtdcHvVJ3SkCludouoXblGr78ic4OX5PPEaIvzaHRhm5zZctb9GhbVKEiUTwZOpC74tT/zhWyiHS/Q1i/2Nh/jik87JO2zHFJhjqewxPKPb50a81GoK8q0V349gjAhoNuJpoYrWIoy9lQAsZtJgwGA+D4J6pzFg9TISbGxmnAE2Sksyl6772MQhSgQ2FK0PMX6gUKAsbJAtqiu5G4+56/UWCIOabgF0pRAvweG347kbRmOpAERJebalXAxVXmqeTizpdVwbV1fJu0KTIsc6ghYiTTdIuHQ0XX/3NsaZScYGm9k2FN9d3Q0f/76/Jo3RNkw3dNfJA17farKm6hGryCp1rQ06nmr8kVFhuARjKhXWoxZjwmJZn4frsF4u43XTD6s33qnJnOkWNZrzDR0+EAIMII/dBIPMsGnRrS5YsQK2banSZdANljTOHNSSqipUircR/QcjHGKCfv8twxvcJG5K2WS5QT4P1sWd2q8HJ6f7NPPd2Eig0/J9I+BvSqUCRm78a5v2IrkmbH38c+3wVxNX09v/07/f1/nYNiUeVmIOw4PFhLh/n+ve/LpmbC1N60XpCQnUk48dFXXjmF/FwuFKLd0sR7u/uRk3mB0MX6bYJBPI6Lfe31p7Yssc6mkD0Vb4AsF+/GoUtiLhS+T94ggivB15dzqlkv9TEbk+JfJwYmrOfqVTcG9z5L2uNCRrefwFqPj4A/76Ly/NerI='

def run():
    base_dir = 'tests/generalization/holdout'
    os.makedirs(base_dir, exist_ok=True)
    fixtures = json.loads(zlib.decompress(base64.b64decode(PAYLOAD)).decode())
    for name, files in fixtures.items():
        path = os.path.join(base_dir, name)
        os.makedirs(path, exist_ok=True)
        for fname, content in files.items():
            fpath = os.path.join(path, fname)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, 'w') as f:
                f.write(content)
    print(f'Generated {len(fixtures)} holdout fixtures.')

if __name__ == '__main__':
    run()
