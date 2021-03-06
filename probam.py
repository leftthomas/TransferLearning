import cv2
import numpy as np
import torch
import torchvision.transforms as transforms


class ProbAM:
    def __init__(self, model):
        self.model = model.eval()

    def __call__(self, images):
        image_size = (images.size(-1), images.size(-2))

        for name, module in self.model.named_children():
            if name == 'conv1':
                out = module(images)
                conv1_heat_maps = out.mean(dim=1, keepdim=True)
            elif name == 'features':
                out = module(out)
                features = out
            elif name == 'classifier':
                out = out.permute(0, 2, 3, 1)
                out = out.contiguous().view(out.size(0), -1, module.weight.size(-1))
                out, probs = module(out)
                classes = out.norm(dim=-1)
                prob = (probs * classes.unsqueeze(dim=-1)).sum(dim=1)
                prob = prob.view(prob.size(0), *features.size()[-2:], -1)
                prob = prob.permute(0, 3, 1, 2).sum(dim=1)

                features_heat_maps = []
                for i in range(prob.size(0)):
                    img = images[i].detach().cpu().numpy()
                    img = img - np.min(img)
                    if np.max(img) != 0:
                        img = img / np.max(img)
                    mask = cv2.resize(prob[i].detach().cpu().numpy(), image_size)
                    mask = mask - np.min(mask)
                    if np.max(mask) != 0:
                        mask = mask / np.max(mask)
                    heat_map = np.float32(cv2.applyColorMap(np.uint8(255 * mask), cv2.COLORMAP_JET))
                    cam = heat_map + np.float32((np.uint8(img.transpose((1, 2, 0)) * 255)))
                    cam = cam - np.min(cam)
                    if np.max(cam) != 0:
                        cam = cam / np.max(cam)
                    features_heat_maps.append(
                        transforms.ToTensor()(cv2.cvtColor(np.uint8(255 * cam), cv2.COLOR_BGR2RGB)))
                features_heat_maps = torch.stack(features_heat_maps)
        return conv1_heat_maps, features_heat_maps
