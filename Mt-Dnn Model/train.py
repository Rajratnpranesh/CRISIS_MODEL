# Copyright (c) Microsoft. All rights reserved.
import argparse
import json
import os
import random
from datetime import datetime
from pprint import pprint
import numpy as np
import torch
from pytorch_pretrained_bert.modeling import BertConfig
from tensorboardX import SummaryWriter
#from torch.utils.tensorboard import SummaryWriter
from experiments.exp_def import TaskDefs
from experiments.glue.glue_utils import submit, eval_model
from data_utils.log_wrapper import create_logger
from data_utils.utils import set_environment
from data_utils.task_def import TaskType, EncoderModelType
from mt_dnn.batcher import BatchGen
from mt_dnn.model import MTDNNModel


def model_config(parser):
    parser.add_argument('--update_bert_opt', default=0, type=int)
    parser.add_argument('--multi_gpu_on', action='store_true')
    parser.add_argument('--mem_cum_type', type=str, default='simple',
                        help='bilinear/simple/defualt')
    parser.add_argument('--answer_num_turn', type=int, default=5)
    parser.add_argument('--answer_mem_drop_p', type=float, default=0.1)
    parser.add_argument('--answer_att_hidden_size', type=int, default=128)
    parser.add_argument('--answer_att_type', type=str, default='bilinear',
                        help='bilinear/simple/defualt')
    parser.add_argument('--answer_rnn_type', type=str, default='gru',
                        help='rnn/gru/lstm')
    parser.add_argument('--answer_sum_att_type', type=str, default='bilinear',
                        help='bilinear/simple/defualt')
    parser.add_argument('--answer_merge_opt', type=int, default=1)
    parser.add_argument('--answer_mem_type', type=int, default=1)
    parser.add_argument('--answer_dropout_p', type=float, default=0.1)
    parser.add_argument('--answer_weight_norm_on', action='store_true')
    parser.add_argument('--dump_state_on', action='store_true')
    parser.add_argument('--answer_opt', type=int, default=0, help='0,1')
    parser.add_argument('--label_size', type=str, default='3')
    parser.add_argument('--mtl_opt', type=int, default=0)
    parser.add_argument('--ratio', type=float, default=0)
    parser.add_argument('--mix_opt', type=int, default=0)
    parser.add_argument('--max_seq_len', type=int, default=512)
    parser.add_argument('--init_ratio', type=float, default=1)
    parser.add_argument('--encoder_type', type=int, default=EncoderModelType.BERT)

    return parser


def data_config(parser):
    parser.add_argument('--log_file', default='mt-dnn-train.log', help='path for log file.')
    parser.add_argument('--tensorboard', action='store_true')
    parser.add_argument('--tensorboard_logdir', default='tensorboard_logdir')
    parser.add_argument("--init_checkpoint", default='mt_dnn_models/bert_model_base.pt', type=str)
    parser.add_argument('--data_dir', default='data/canonical_data/bert_uncased_lower')
    parser.add_argument('--data_sort_on', action='store_true')
    parser.add_argument('--name', default='farmer')
    parser.add_argument('--task_def', type=str, default="experiments/glue/glue_task_def.yml")
    parser.add_argument('--train_datasets', default='sst')
    parser.add_argument('--test_datasets', default='sst')
    return parser


def train_config(parser):
    parser.add_argument('--cuda', type=bool, default=torch.cuda.is_available(),
                        help='whether to use GPU acceleration.')
    parser.add_argument('--log_per_updates', type=int, default=500)
    parser.add_argument('--save_per_updates', type=int, default=10000)
    parser.add_argument('--save_per_updates_on', action='store_true')
    parser.add_argument('--epochs', type=int, default=15)
    parser.add_argument('--batch_size', type=int, default=8)
    parser.add_argument('--batch_size_eval', type=int, default=8)
    parser.add_argument('--optimizer', default='adamax',
                        help='supported optimizer: adamax, sgd, adadelta, adam')
    parser.add_argument('--grad_clipping', type=float, default=0)
    parser.add_argument('--global_grad_clipping', type=float, default=1.0)
    parser.add_argument('--weight_decay', type=float, default=0)
    parser.add_argument('--learning_rate', type=float, default=5e-5)
    parser.add_argument('--momentum', type=float, default=0)
    parser.add_argument('--warmup', type=float, default=0.1)
    parser.add_argument('--warmup_schedule', type=str, default='warmup_linear')
    parser.add_argument('--adam_eps', type=float, default=1e-6)

    parser.add_argument('--vb_dropout', action='store_false')
    parser.add_argument('--dropout_p', type=float, default=0.1)
    parser.add_argument('--dropout_w', type=float, default=0.000)
    parser.add_argument('--bert_dropout_p', type=float, default=0.1)

    # loading
    parser.add_argument("--model_ckpt", default='checkpoints/model_0.pt', type=str)
    parser.add_argument("--resume", action='store_true')

    # EMA
    parser.add_argument('--ema_opt', type=int, default=0)
    parser.add_argument('--ema_gamma', type=float, default=0.995)

    # scheduler
    parser.add_argument('--have_lr_scheduler', dest='have_lr_scheduler', action='store_false')
    parser.add_argument('--multi_step_lr', type=str, default='10,20,30')
    parser.add_argument('--freeze_layers', type=int, default=-1)
    parser.add_argument('--embedding_opt', type=int, default=0)
    parser.add_argument('--lr_gamma', type=float, default=0.5)
    parser.add_argument('--bert_l2norm', type=float, default=0.0)
    parser.add_argument('--scheduler_type', type=str, default='ms', help='ms/rop/exp')
    parser.add_argument('--output_dir', default='checkpoint')
    parser.add_argument('--seed', type=int, default=2018,
                        help='random seed for data shuffling, embedding init, etc.')
    parser.add_argument('--grad_accumulation_step', type=int, default=1)

    #fp 16
    parser.add_argument('--fp16', action='store_true',
                        help="Whether to use 16-bit (mixed) precision (through NVIDIA apex) instead of 32-bit")
    parser.add_argument('--fp16_opt_level', type=str, default='O1',
                        help="For fp16: Apex AMP optimization level selected in ['O0', 'O1', 'O2', and 'O3']."
                             "See details at https://nvidia.github.io/apex/amp.html")
    return parser


parser = argparse.ArgumentParser()
parser = data_config(parser)
parser = model_config(parser)
parser = train_config(parser)
args = parser.parse_args()

output_dir = args.output_dir
data_dir = args.data_dir
args.train_datasets = args.train_datasets.split(',')
args.test_datasets = args.test_datasets.split(',')
pprint(args)

os.makedirs(output_dir, exist_ok=True)
output_dir = os.path.abspath(output_dir)

set_environment(args.seed, args.cuda)
log_path = args.log_file
logger = create_logger(__name__, to_disk=True, log_file=log_path)
logger.info(args.answer_opt)

task_defs = TaskDefs(args.task_def)
encoder_type = task_defs.encoderType
args.encoder_type = encoder_type


def dump(path, data):
    with open(path, 'w') as f:
        json.dump(data, f)


def generate_decoder_opt(enable_san, max_opt):
    opt_v = 0
    if enable_san and max_opt < 3:
        opt_v = max_opt
    return opt_v


def main():
    logger.info('Launching the MT-DNN training')
    opt = vars(args)
    # update data dir
    opt['data_dir'] = data_dir
    batch_size = args.batch_size
    train_data_list = []
    tasks = {}
    tasks_class = {}
    nclass_list = []
    decoder_opts = []
    task_types = []
    dropout_list = []
    for dataset in args.train_datasets:
        prefix = dataset.split('_')[0]
        if prefix in tasks: continue
        assert prefix in task_defs.n_class_map
        assert prefix in task_defs.data_type_map
        data_type = task_defs.data_type_map[prefix]
        nclass = task_defs.n_class_map[prefix]
        task_id = len(tasks)
        if args.mtl_opt > 0:
            task_id = tasks_class[nclass] if nclass in tasks_class else len(tasks_class)

        task_type = task_defs.task_type_map[prefix]

        dopt = generate_decoder_opt(task_defs.enable_san_map[prefix], opt['answer_opt'])
        if task_id < len(decoder_opts):
            decoder_opts[task_id] = min(decoder_opts[task_id], dopt)
        else:
            decoder_opts.append(dopt)
        task_types.append(task_type)

        if prefix not in tasks:
            tasks[prefix] = len(tasks)
            if args.mtl_opt < 1: nclass_list.append(nclass)

        if (nclass not in tasks_class):
            tasks_class[nclass] = len(tasks_class)
            if args.mtl_opt > 0: nclass_list.append(nclass)

        dropout_p = task_defs.dropout_p_map.get(prefix, args.dropout_p)
        dropout_list.append(dropout_p)

        train_path = os.path.join(data_dir, '{}_train.json'.format(dataset))
        logger.info('Loading {} as task {}'.format(train_path, task_id))
        train_data = BatchGen(BatchGen.load(train_path, True, task_type=task_type, maxlen=args.max_seq_len),
                              batch_size=batch_size,
                              dropout_w=args.dropout_w,
                              gpu=args.cuda,
                              task_id=task_id,
                              maxlen=args.max_seq_len,
                              data_type=data_type,
                              task_type=task_type,
                              encoder_type=encoder_type)
        train_data_list.append(train_data)

    opt['answer_opt'] = decoder_opts
    opt['task_types'] = task_types
    opt['tasks_dropout_p'] = dropout_list

    args.label_size = ','.join([str(l) for l in nclass_list])
    logger.info(args.label_size)
    dev_data_list = []
    test_data_list = []
    for dataset in args.test_datasets:
        prefix = dataset.split('_')[0]
        task_id = tasks_class[task_defs.n_class_map[prefix]] if args.mtl_opt > 0 else tasks[prefix]
        task_type = task_defs.task_type_map[prefix]

        pw_task = False
        if task_type == TaskType.Ranking:
            pw_task = True

        assert prefix in task_defs.data_type_map
        data_type = task_defs.data_type_map[prefix]

        dev_path = os.path.join(data_dir, '{}_dev.json'.format(dataset))
        dev_data = None
        if os.path.exists(dev_path):
            dev_data = BatchGen(BatchGen.load(dev_path, False, task_type=task_type, maxlen=args.max_seq_len),
                                batch_size=args.batch_size_eval,
                                gpu=args.cuda, is_train=False,
                                task_id=task_id,
                                maxlen=args.max_seq_len,
                                data_type=data_type,
                                task_type=task_type,
                                encoder_type=encoder_type)
        dev_data_list.append(dev_data)

        test_path = os.path.join(data_dir, '{}_test.json'.format(dataset))
        test_data = None
        if os.path.exists(test_path):
            test_data = BatchGen(BatchGen.load(test_path, False, task_type=task_type, maxlen=args.max_seq_len),
                                 batch_size=args.batch_size_eval,
                                 gpu=args.cuda, is_train=False,
                                 task_id=task_id,
                                 maxlen=args.max_seq_len,
                                 data_type=data_type,
                                 task_type=task_type,
                                 encoder_type=encoder_type)
        test_data_list.append(test_data)

    logger.info('#' * 20)
    logger.info(opt)
    logger.info('#' * 20)

    all_iters = [iter(item) for item in train_data_list]
    all_lens = [len(bg) for bg in train_data_list]

    # div number of grad accumulation. 
    num_all_batches = args.epochs * sum(all_lens) // args.grad_accumulation_step
    logger.info('############# Gradient Accumulation Info #############')
    logger.info('number of step: {}'.format(args.epochs * sum(all_lens)))
    logger.info('number of grad grad_accumulation step: {}'.format(args.grad_accumulation_step))
    logger.info('adjusted number of step: {}'.format(num_all_batches))
    logger.info('############# Gradient Accumulation Info #############')

    if len(train_data_list) > 1 and args.ratio > 0:
        num_all_batches = int(args.epochs * (len(train_data_list[0]) * (1 + args.ratio)))

    bert_model_path = args.init_checkpoint
    state_dict = None

    if encoder_type == EncoderModelType.BERT:
        if os.path.exists(bert_model_path):
            state_dict = torch.load(bert_model_path)
            config = state_dict['config']
            config['attention_probs_dropout_prob'] = args.bert_dropout_p
            config['hidden_dropout_prob'] = args.bert_dropout_p
            opt.update(config)
        else:
            logger.error('#' * 20)
            logger.error('Could not find the init model!\n The parameters will be initialized randomly!')
            logger.error('#' * 20)
            config = BertConfig(vocab_size_or_config_json_file=30522).to_dict()
            opt.update(config)
    elif encoder_type == EncoderModelType.ROBERTA:
        bert_model_path = '{}/model.pt'.format(bert_model_path)
        if os.path.exists(bert_model_path):
            new_state_dict = {}
            state_dict = torch.load(bert_model_path)
            for key, val in state_dict['model'].items():
                if key.startswith('decoder.sentence_encoder'):
                    key = 'bert.model.{}'.format(key)
                    new_state_dict[key] = val
                elif key.startswith('classification_heads'):
                    key = 'bert.model.{}'.format(key)
                    new_state_dict[key] = val
            state_dict = {'state': new_state_dict}

    model = MTDNNModel(opt, state_dict=state_dict, num_train_step=num_all_batches)
    if args.resume and args.model_ckpt:
        logger.info('loading model from {}'.format(args.model_ckpt))
        model.load(args.model_ckpt)

    #### model meta str
    headline = '############# Model Arch of MT-DNN #############'
    ### print network
    logger.info('\n{}\n{}\n'.format(headline, model.network))

    # dump config
    config_file = os.path.join(output_dir, 'config.json')
    with open(config_file, 'w', encoding='utf-8') as writer:
        writer.write('{}\n'.format(json.dumps(opt)))
        writer.write('\n{}\n{}\n'.format(headline, model.network))

    logger.info("Total number of params: {}".format(model.total_param))

    # tensorboard
    if args.tensorboard:
        args.tensorboard_logdir = os.path.join(args.output_dir, args.tensorboard_logdir)
        tensorboard = SummaryWriter(log_dir=args.tensorboard_logdir)

    for epoch in range(0, args.epochs):
        logger.warning('At epoch {}'.format(epoch))
        for train_data in train_data_list:
            train_data.reset()
        start = datetime.now()
        all_indices = []
        if len(train_data_list) > 1 and args.ratio > 0:
            main_indices = [0] * len(train_data_list[0])
            extra_indices = []
            for i in range(1, len(train_data_list)):
                extra_indices += [i] * len(train_data_list[i])
            random_picks = int(min(len(train_data_list[0]) * args.ratio, len(extra_indices)))
            extra_indices = np.random.choice(extra_indices, random_picks, replace=False)
            if args.mix_opt > 0:
                extra_indices = extra_indices.tolist()
                random.shuffle(extra_indices)
                all_indices = extra_indices + main_indices
            else:
                all_indices = main_indices + extra_indices.tolist()

        else:
            for i in range(1, len(train_data_list)):
                all_indices += [i] * len(train_data_list[i])
            if args.mix_opt > 0:
                random.shuffle(all_indices)
            all_indices += [0] * len(train_data_list[0])
        if args.mix_opt < 1:
            random.shuffle(all_indices)

        for i in range(len(all_indices)):
            task_id = all_indices[i]
            batch_meta, batch_data = next(all_iters[task_id])
            model.update(batch_meta, batch_data)
            if (model.local_updates) % (args.log_per_updates * args.grad_accumulation_step) == 0 or model.local_updates == 1:
                ramaining_time = str((datetime.now() - start) / (i + 1) * (len(all_indices) - i - 1)).split('.')[0]
                logger.info('Task [{0:2}] updates[{1:6}] train loss[{2:.5f}] remaining[{3}]'.format(task_id,
                                                                                                    model.updates,
                                                                                                    model.train_loss.avg,
                                                                                                    ramaining_time))
                if args.tensorboard:
                    tensorboard.add_scalar('train/loss', model.train_loss.avg, global_step=model.updates)


            if args.save_per_updates_on and ((model.local_updates) % (args.save_per_updates * args.grad_accumulation_step) == 0):
                model_file = os.path.join(output_dir, 'model_{}_{}.pt'.format(epoch, model.updates))
                logger.info('Saving mt-dnn model to {}'.format(model_file))
                model.save(model_file)

        for idx, dataset in enumerate(args.test_datasets):
            prefix = dataset.split('_')[0]
            label_dict = task_defs.global_map.get(prefix, None)
            dev_data = dev_data_list[idx]
            if dev_data is not None:
                with torch.no_grad():
                    dev_metrics, dev_predictions, scores, golds, dev_ids= eval_model(model,
                                                                                    dev_data,
                                                                                    metric_meta=task_defs.metric_meta_map[prefix],
                                                                                    use_cuda=args.cuda)
                for key, val in dev_metrics.items():
                    if args.tensorboard:
                        tensorboard.add_scalar('dev/{}/{}'.format(dataset, key), val, global_step=epoch)
                    logger.warning('Task {0} -- epoch {1} -- Dev {2}: {3:.3f}'.format(dataset, epoch, key, val))
                score_file = os.path.join(output_dir, '{}_dev_scores_{}.json'.format(dataset, epoch))
                results = {'metrics': dev_metrics, 'predictions': dev_predictions, 'uids': dev_ids, 'scores': scores}
                dump(score_file, results)
                official_score_file = os.path.join(output_dir, '{}_dev_scores_{}.tsv'.format(dataset, epoch))
                submit(official_score_file, results, label_dict)

            # test eval
            test_data = test_data_list[idx]
            if test_data is not None:
                with torch.no_grad():
                    test_metrics, test_predictions, scores, golds, test_ids= eval_model(model, test_data,
                                                                                        metric_meta=task_defs.metric_meta_map[prefix],
                                                                                        use_cuda=args.cuda, with_label=False)
                score_file = os.path.join(output_dir, '{}_test_scores_{}.json'.format(dataset, epoch))
                results = {'metrics': test_metrics, 'predictions': test_predictions, 'uids': test_ids, 'scores': scores}
                dump(score_file, results)
                official_score_file = os.path.join(output_dir, '{}_test_scores_{}.tsv'.format(dataset, epoch))
                submit(official_score_file, results, label_dict)
                logger.info('[new test scores saved.]')

        model_file = os.path.join(output_dir, 'model_{}.pt'.format(epoch))
        model.save(model_file)
    if args.tensorboard:
        tensorboard.close()

if __name__ == '__main__':
    main()

