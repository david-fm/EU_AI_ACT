import numpy as np

from eu_ai_act.adapters import InMemoryDatasetAdapter, KerasModelAdapter, PyTorchModelAdapter, TensorFlowModelAdapter


def test_in_memory_dataset_adapter_batches_and_metadata():
    adapter = InMemoryDatasetAdapter(
        features=[[1, 2], [3, 4], [5, 6]],
        labels=[0, 1, 0],
        metadata=[{"age": 10, "site": "a"}, {"age": 11, "site": "b"}, {"age": 12, "site": "a"}],
    )

    batches = list(adapter.iter_batches(batch_size=2))

    assert len(batches) == 2
    assert adapter.get_metadata_fields() == ("age", "site")
    assert batches[0][0] == [[1, 2], [3, 4]]
    assert batches[0][1] == [0, 1]
    assert batches[0][2] == [{"age": 10, "site": "a"}, {"age": 11, "site": "b"}]


def test_keras_model_adapter_predicts_numpy_output():
    from keras import Sequential
    from keras import layers

    model = Sequential(
        [
            layers.Input(shape=(2,)),
            layers.Dense(1, kernel_initializer="ones", bias_initializer="zeros"),
        ]
    )
    adapter = KerasModelAdapter(model=model, model_name="keras-demo")

    prediction = adapter.predict(np.array([[1.0, 2.0]], dtype=np.float32))

    assert adapter.get_model_metadata()["framework"] == "keras"
    assert prediction.metadata == {"framework": "keras"}
    assert prediction.scores == [[3.0]]


def test_tensorflow_model_adapter_predicts_tensor_output():
    import tensorflow as tf

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(2,)),
            tf.keras.layers.Dense(1, kernel_initializer="ones", bias_initializer="zeros"),
        ]
    )
    adapter = TensorFlowModelAdapter(model=model, model_name="tf-demo")

    prediction = adapter.predict(tf.constant([[1.0, 2.0]], dtype=tf.float32))

    assert adapter.get_model_metadata()["framework"] == "tensorflow"
    assert prediction.metadata == {"framework": "tensorflow"}
    assert prediction.scores == [[3.0]]


def test_pytorch_model_adapter_uses_torch_like_interface(monkeypatch):
    class FakeTensor:
        def __init__(self, value):
            self.value = value

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return np.array(self.value)

    class FakeTorch:
        Tensor = FakeTensor

        class _NoGrad:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

        @staticmethod
        def no_grad():
            return FakeTorch._NoGrad()

        @staticmethod
        def as_tensor(inputs):
            return FakeTensor(inputs)

    class FakeModel:
        def __init__(self):
            self.seen = None

        def eval(self):
            return None

        def __call__(self, inputs):
            self.seen = inputs
            return FakeTensor([[5.0]])

    from eu_ai_act.adapters import pytorch_adapter as pytorch_module

    monkeypatch.setattr(pytorch_module, "_import_torch", lambda: FakeTorch)

    model = FakeModel()
    adapter = PyTorchModelAdapter(model=model, model_name="torch-demo")

    prediction = adapter.predict([[1.0, 2.0]])

    assert model.seen.value == [[1.0, 2.0]]
    assert prediction.metadata == {"framework": "pytorch"}
    assert prediction.scores == [[5.0]]